"""Claude Code CLI Runner for HELIX v4.

Manages Claude Code CLI subprocess execution.
"""

import asyncio
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .llm_client import LLMClient


@dataclass
class ClaudeResult:
    """Result from a Claude Code CLI execution.

    Attributes:
        success: Whether the execution completed successfully.
        exit_code: Process exit code.
        stdout: Standard output from the process.
        stderr: Standard error from the process.
        output_json: Parsed JSON output if available.
        duration_seconds: Execution duration in seconds.
    """
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    output_json: dict[str, Any] | None = None
    duration_seconds: float = 0.0


class ClaudeRunner:
    """Runs Claude Code CLI as a subprocess for phase execution.

    The ClaudeRunner manages the execution of Claude Code CLI,
    handling environment setup, process management, and output
    collection.

    Example:
        runner = ClaudeRunner()
        result = await runner.run_phase(
            phase_dir=Path("/project/phases/01-foundation"),
            model="claude-3-opus"
        )
        if result.success:
            print("Phase completed successfully")
        else:
            print(f"Phase failed: {result.stderr}")
    """

    DEFAULT_CLAUDE_CMD = "claude"
    DEFAULT_TIMEOUT = 1800

    def __init__(
        self,
        claude_cmd: str | None = None,
        llm_client: LLMClient | None = None,
    ) -> None:
        """Initialize the ClaudeRunner.

        Args:
            claude_cmd: Path to the Claude Code CLI executable.
                       Defaults to "claude" (uses PATH).
            llm_client: Optional LLMClient for model resolution.
        """
        self.claude_cmd = claude_cmd or self.DEFAULT_CLAUDE_CMD
        self.llm_client = llm_client or LLMClient()

    async def run_phase(
        self,
        phase_dir: Path,
        model: str | None = None,
        prompt: str | None = None,
        timeout: int | None = None,
        env_overrides: dict[str, str] | None = None,
    ) -> ClaudeResult:
        """Run Claude Code CLI for a phase.

        Args:
            phase_dir: Path to the phase directory.
            model: Optional model spec to use.
            prompt: Optional initial prompt. Defaults to reading CLAUDE.md.
            timeout: Optional timeout in seconds.
            env_overrides: Optional environment variable overrides.

        Returns:
            ClaudeResult with execution details.
        """
        import time

        start_time = time.time()

        env = self.get_claude_env(model)
        if env_overrides:
            env.update(env_overrides)

        if prompt is None:
            claude_md = phase_dir / "CLAUDE.md"
            if claude_md.exists():
                prompt = f"Read CLAUDE.md and execute all tasks described there."
            else:
                prompt = "Execute the phase tasks as defined in the spec."

        cmd = [
            self.claude_cmd,
            "--print",
            "--dangerously-skip-permissions",
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=phase_dir,
                env={**os.environ, **env},
            )

            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(input=prompt.encode("utf-8")),
                timeout=timeout or self.DEFAULT_TIMEOUT,
            )

            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")
            exit_code = process.returncode or 0

            output_json = self._extract_json_output(stdout, phase_dir)

            duration = time.time() - start_time

            return ClaudeResult(
                success=exit_code == 0,
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                output_json=output_json,
                duration_seconds=duration,
            )

        except asyncio.TimeoutError:
            duration = time.time() - start_time
            return ClaudeResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr=f"Timeout after {timeout or self.DEFAULT_TIMEOUT} seconds",
                duration_seconds=duration,
            )
        except FileNotFoundError:
            duration = time.time() - start_time
            return ClaudeResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr=f"Claude CLI not found: {self.claude_cmd}",
                duration_seconds=duration,
            )
        except Exception as e:
            duration = time.time() - start_time
            return ClaudeResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr=str(e),
                duration_seconds=duration,
            )

    def get_claude_env(self, model_spec: str | None = None) -> dict[str, str]:
        """Get environment variables for Claude CLI execution.

        Args:
            model_spec: Optional model spec to configure.

        Returns:
            Dictionary of environment variables to set.
        """
        env: dict[str, str] = {}

        if model_spec:
            try:
                config = self.llm_client.resolve_model(model_spec)

                api_key = os.environ.get(config.api_key_env, "")
                if api_key:
                    if config.provider == "anthropic":
                        env["ANTHROPIC_API_KEY"] = api_key
                    elif config.provider == "openai":
                        env["OPENAI_API_KEY"] = api_key

                env["CLAUDE_MODEL"] = config.model_id

            except ValueError:
                env["CLAUDE_MODEL"] = model_spec

        return env

    def _extract_json_output(
        self, stdout: str, phase_dir: Path
    ) -> dict[str, Any] | None:
        """Extract JSON output from Claude execution.

        Looks for JSON in stdout or in output/result.json.

        Args:
            stdout: Standard output from the process.
            phase_dir: Phase directory to check for output files.

        Returns:
            Parsed JSON dictionary or None.
        """
        result_file = phase_dir / "output" / "result.json"
        if result_file.exists():
            try:
                with open(result_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass

        json_start = stdout.rfind("```json")
        if json_start != -1:
            json_end = stdout.find("```", json_start + 7)
            if json_end != -1:
                json_str = stdout[json_start + 7:json_end].strip()
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    pass

        for line in reversed(stdout.split("\n")):
            line = line.strip()
            if line.startswith("{") and line.endswith("}"):
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    continue

        return None

    async def run_with_retry(
        self,
        phase_dir: Path,
        model: str | None = None,
        max_retries: int = 3,
        retry_delay: float = 5.0,
        **kwargs: Any,
    ) -> ClaudeResult:
        """Run Claude CLI with automatic retries.

        Args:
            phase_dir: Path to the phase directory.
            model: Optional model spec to use.
            max_retries: Maximum number of retry attempts.
            retry_delay: Delay between retries in seconds.
            **kwargs: Additional arguments for run_phase.

        Returns:
            ClaudeResult from the successful run or last attempt.
        """
        last_result: ClaudeResult | None = None

        for attempt in range(max_retries + 1):
            result = await self.run_phase(phase_dir, model, **kwargs)

            if result.success:
                return result

            last_result = result

            if attempt < max_retries:
                await asyncio.sleep(retry_delay)

        return last_result or ClaudeResult(
            success=False,
            exit_code=-1,
            stdout="",
            stderr="No attempts were made",
        )

    async def check_availability(self) -> bool:
        """Check if Claude CLI is available.

        Returns:
            True if Claude CLI is installed and accessible.
        """
        try:
            process = await asyncio.create_subprocess_exec(
                self.claude_cmd,
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.wait_for(process.communicate(), timeout=10.0)
            return process.returncode == 0
        except (FileNotFoundError, asyncio.TimeoutError):
            return False
