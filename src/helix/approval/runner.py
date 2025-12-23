"""Sub-Agent Approval Runner for HELIX v4.

Spawns independent Claude Code instances for approval checks.
This is Layer 4 of the validation system - semantic deep checks.

The ApprovalRunner creates a new Claude Code process with a fresh
context to perform unbiased validation. The sub-agent runs in a
dedicated approvals/ directory with its own CLAUDE.md instructions.

Example:
    >>> from helix.approval import ApprovalRunner
    >>> from pathlib import Path
    >>>
    >>> runner = ApprovalRunner()
    >>> result = await runner.run_approval(
    ...     approval_type="adr",
    ...     input_files=[Path("output/ADR-feature.md")],
    ... )
    >>> if result.approved:
    ...     print("ADR approved!")

See Also:
    - ADR-015: Approval & Validation System
    - approvals/adr/CLAUDE.md: Sub-Agent instructions
"""

import asyncio
import json
import os
import shutil
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .result import ApprovalResult, Finding, Severity


@dataclass
class ApprovalConfig:
    """Configuration for an approval run.

    Controls how the sub-agent approval is executed.

    Attributes:
        approval_type: Type of approval (e.g., "adr", "code")
        model: Claude model to use (default: claude-sonnet-4-20250514)
        timeout: Maximum time for approval in seconds
        retry_on_failure: Whether to retry if sub-agent fails
        required_confidence: Minimum confidence for auto-approve

    Example:
        >>> config = ApprovalConfig(
        ...     approval_type="adr",
        ...     timeout=300,
        ...     required_confidence=0.9,
        ... )
    """
    approval_type: str
    model: str = "claude-sonnet-4-20250514"
    timeout: int = 300  # 5 minutes
    retry_on_failure: bool = True
    required_confidence: float = 0.8


class ApprovalRunner:
    """Runs approval checks using sub-agents.

    The ApprovalRunner spawns a new Claude Code CLI instance
    with a fresh context to perform independent validation.

    The sub-agent:
    - Runs in approvals/<type>/ directory
    - Reads input files from approvals/<type>/input/
    - Follows instructions from approvals/<type>/CLAUDE.md
    - Writes result to approvals/<type>/output/approval-result.json

    Attributes:
        approvals_base: Base directory for approval definitions
        claude_cmd: Path to Claude CLI executable

    Example:
        >>> runner = ApprovalRunner()
        >>> result = await runner.run_approval(
        ...     approval_type="adr",
        ...     input_files=[Path("output/ADR-feature.md")],
        ... )
        >>> if result.approved:
        ...     print("Approved!")
        >>> else:
        ...     for finding in result.errors:
        ...         print(f"Error: {finding.message}")
    """

    # Default paths
    APPROVALS_DIR = Path("approvals")
    CLAUDE_CMD = "claude"

    def __init__(
        self,
        approvals_base: Optional[Path] = None,
        claude_cmd: Optional[str] = None,
    ) -> None:
        """Initialize the ApprovalRunner.

        Args:
            approvals_base: Base directory for approval definitions.
                           Default: approvals/
            claude_cmd: Path to Claude CLI executable.
                       Default: "claude"
        """
        self.approvals_base = approvals_base or self.APPROVALS_DIR
        self.claude_cmd = claude_cmd or self.CLAUDE_CMD

    async def run_approval(
        self,
        approval_type: str,
        input_files: list[Path],
        config: Optional[ApprovalConfig] = None,
    ) -> ApprovalResult:
        """Run an approval check using a sub-agent.

        Prepares the approval directory, spawns a Claude CLI process,
        and parses the resulting approval-result.json.

        Args:
            approval_type: Type of approval (e.g., "adr", "code").
            input_files: Files to check.
            config: Optional configuration.

        Returns:
            ApprovalResult with findings and decision.

        Example:
            >>> result = await runner.run_approval(
            ...     approval_type="adr",
            ...     input_files=[Path("output/ADR-015.md")],
            ... )
        """
        config = config or ApprovalConfig(approval_type=approval_type)
        approval_id = str(uuid.uuid4())[:8]
        start_time = datetime.now()

        # Validate approval type exists
        approval_dir = self.approvals_base / approval_type
        if not approval_dir.exists():
            return self._create_error_result(
                approval_id=approval_id,
                approval_type=approval_type,
                check="setup",
                message=f"Approval type not found: {approval_type}",
            )

        # Check CLAUDE.md exists
        claude_md = approval_dir / "CLAUDE.md"
        if not claude_md.exists():
            return self._create_error_result(
                approval_id=approval_id,
                approval_type=approval_type,
                check="setup",
                message=f"CLAUDE.md not found in {approval_dir}",
            )

        # Prepare input directory
        input_dir = approval_dir / "input"
        output_dir = approval_dir / "output"

        try:
            self._prepare_directories(input_dir, output_dir)
            self._link_input_files(input_files, input_dir)
        except Exception as e:
            return self._create_error_result(
                approval_id=approval_id,
                approval_type=approval_type,
                check="setup",
                message=f"Failed to prepare directories: {e}",
            )

        # Build prompt for sub-agent
        prompt = self._build_prompt(approval_type, input_files)

        # Spawn sub-agent
        try:
            await self._spawn_agent(
                approval_dir=approval_dir,
                prompt=prompt,
                timeout=config.timeout,
            )
        except asyncio.TimeoutError:
            duration = (datetime.now() - start_time).total_seconds()
            return ApprovalResult(
                approval_id=approval_id,
                approval_type=approval_type,
                result="rejected",
                confidence=0.0,
                findings=[Finding(
                    severity=Severity.ERROR,
                    check="timeout",
                    message=f"Approval timed out after {config.timeout}s",
                )],
                duration_seconds=duration,
            )
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            return ApprovalResult(
                approval_id=approval_id,
                approval_type=approval_type,
                result="rejected",
                confidence=0.0,
                findings=[Finding(
                    severity=Severity.ERROR,
                    check="spawn",
                    message=f"Failed to spawn sub-agent: {e}",
                )],
                duration_seconds=duration,
            )

        # Parse result
        duration = (datetime.now() - start_time).total_seconds()
        result = self._parse_result(
            approval_id=approval_id,
            approval_type=approval_type,
            output_dir=output_dir,
            duration=duration,
        )

        return result

    def _prepare_directories(
        self,
        input_dir: Path,
        output_dir: Path,
    ) -> None:
        """Prepare input and output directories.

        Creates directories if needed and cleans previous content.

        Args:
            input_dir: Directory for input files
            output_dir: Directory for output files
        """
        # Create directories
        input_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Clean previous inputs (remove old symlinks)
        for old_file in input_dir.iterdir():
            if old_file.is_symlink() or old_file.is_file():
                old_file.unlink()

        # Clean previous outputs
        for old_file in output_dir.iterdir():
            if old_file.is_file():
                old_file.unlink()

    def _link_input_files(
        self,
        input_files: list[Path],
        input_dir: Path,
    ) -> None:
        """Create symlinks for input files.

        Uses symlinks instead of copying so the sub-agent sees
        the original paths and can understand the codebase context.

        Args:
            input_files: Files to link
            input_dir: Directory to create links in
        """
        for input_file in input_files:
            if not input_file.exists():
                continue

            abs_path = input_file.absolute()
            link_path = input_dir / input_file.name

            # Remove existing link if present
            if link_path.exists() or link_path.is_symlink():
                link_path.unlink()

            os.symlink(abs_path, link_path)

    async def _spawn_agent(
        self,
        approval_dir: Path,
        prompt: str,
        timeout: int,
    ) -> None:
        """Spawn a sub-agent process.

        Runs Claude CLI with --print flag to get non-interactive
        execution. The sub-agent runs in the approval directory
        and follows the CLAUDE.md instructions.

        Args:
            approval_dir: Working directory for the agent.
            prompt: Prompt to send to the agent.
            timeout: Timeout in seconds.

        Raises:
            asyncio.TimeoutError: If timeout exceeded
            Exception: If process fails to spawn
        """
        # Build command
        cmd = [
            self.claude_cmd,
            "--print",
            "--dangerously-skip-permissions",
        ]

        # Spawn process
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=approval_dir,
        )

        # Send prompt and wait for completion
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=prompt.encode()),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            # Kill the process on timeout
            try:
                process.kill()
                await process.wait()
            except Exception:
                pass
            raise

        # Check return code
        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            raise RuntimeError(f"Sub-agent failed (code {process.returncode}): {error_msg}")

    def _build_prompt(
        self,
        approval_type: str,
        input_files: list[Path],
    ) -> str:
        """Build the prompt for the sub-agent.

        Creates a prompt that instructs the sub-agent to read
        CLAUDE.md and perform the approval checks.

        Args:
            approval_type: Type of approval.
            input_files: Files being checked.

        Returns:
            Prompt string for the sub-agent.
        """
        file_list = ", ".join(f.name for f in input_files)

        return f"""Lies CLAUDE.md und führe eine {approval_type.upper()}-Freigabeprüfung durch.

Zu prüfende Dateien (in input/):
{file_list}

Führe ALLE Checks in checks/ aus und schreibe das Ergebnis nach:
output/approval-result.json

Halte dich strikt an das Output-Format aus CLAUDE.md.

WICHTIG:
- Erstelle output/approval-result.json als letzte Aktion
- Das JSON muss valide sein
- Alle Findings müssen dokumentiert werden"""

    def _parse_result(
        self,
        approval_id: str,
        approval_type: str,
        output_dir: Path,
        duration: float,
    ) -> ApprovalResult:
        """Parse the approval result from the sub-agent output.

        Reads the approval-result.json file and converts it to
        an ApprovalResult object.

        Args:
            approval_id: Unique ID for this approval
            approval_type: Type of approval
            output_dir: Directory containing output files
            duration: How long the approval took

        Returns:
            ApprovalResult parsed from JSON or error result
        """
        output_file = output_dir / "approval-result.json"

        if not output_file.exists():
            return ApprovalResult(
                approval_id=approval_id,
                approval_type=approval_type,
                result="rejected",
                confidence=0.0,
                findings=[Finding(
                    severity=Severity.ERROR,
                    check="output",
                    message="No approval result file generated",
                )],
                duration_seconds=duration,
            )

        try:
            with open(output_file, encoding="utf-8") as f:
                result_data = json.load(f)
        except json.JSONDecodeError as e:
            return ApprovalResult(
                approval_id=approval_id,
                approval_type=approval_type,
                result="rejected",
                confidence=0.0,
                findings=[Finding(
                    severity=Severity.ERROR,
                    check="parse",
                    message=f"Invalid JSON in result file: {e}",
                )],
                duration_seconds=duration,
            )
        except Exception as e:
            return ApprovalResult(
                approval_id=approval_id,
                approval_type=approval_type,
                result="rejected",
                confidence=0.0,
                findings=[Finding(
                    severity=Severity.ERROR,
                    check="parse",
                    message=f"Failed to read result file: {e}",
                )],
                duration_seconds=duration,
            )

        # Parse the result
        try:
            result = ApprovalResult.from_dict(
                approval_id=approval_id,
                approval_type=approval_type,
                data=result_data,
            )
            result.duration_seconds = duration
            return result
        except (KeyError, ValueError) as e:
            return ApprovalResult(
                approval_id=approval_id,
                approval_type=approval_type,
                result="rejected",
                confidence=0.0,
                findings=[Finding(
                    severity=Severity.ERROR,
                    check="parse",
                    message=f"Invalid result structure: {e}",
                )],
                duration_seconds=duration,
            )

    def _create_error_result(
        self,
        approval_id: str,
        approval_type: str,
        check: str,
        message: str,
    ) -> ApprovalResult:
        """Create an error result.

        Helper method to create a rejected ApprovalResult with
        a single error finding.

        Args:
            approval_id: Unique ID
            approval_type: Type of approval
            check: Check name that failed
            message: Error message

        Returns:
            ApprovalResult with single error finding
        """
        return ApprovalResult(
            approval_id=approval_id,
            approval_type=approval_type,
            result="rejected",
            confidence=0.0,
            findings=[Finding(
                severity=Severity.ERROR,
                check=check,
                message=message,
            )],
        )


async def run_approval(
    approval_type: str,
    input_files: list[Path],
    config: Optional[ApprovalConfig] = None,
) -> ApprovalResult:
    """Convenience function to run an approval.

    Creates an ApprovalRunner and runs the approval in one call.

    Args:
        approval_type: Type of approval (e.g., "adr", "code")
        input_files: Files to check
        config: Optional configuration

    Returns:
        ApprovalResult

    Example:
        >>> from helix.approval.runner import run_approval
        >>> result = await run_approval("adr", [Path("output/ADR.md")])
    """
    runner = ApprovalRunner()
    return await runner.run_approval(
        approval_type=approval_type,
        input_files=input_files,
        config=config,
    )
