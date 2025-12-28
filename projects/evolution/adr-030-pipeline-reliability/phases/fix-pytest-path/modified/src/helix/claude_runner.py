"""Claude Code CLI Runner for HELIX v4.

Manages Claude Code CLI subprocess execution with live output streaming.

ADR-030 Fix 1: Added virtualenv PATH support to ensure pytest and other
Python tools are accessible in Claude Code bash sessions. The helix
virtualenv's bin directory is prepended to PATH in all subprocess
environment configurations.
"""

import asyncio
import json
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Awaitable


from .llm_client import LLMClient


# Type alias for output callback
OutputCallback = Callable[[str, str], Awaitable[None]]  # (stream: "stdout"|"stderr", line: str)


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
    collection. Supports live output streaming via callbacks.

    ADR-030 Fix 1: The runner now includes Python virtualenv in PATH
    to ensure pytest and other Python tools are accessible.

    Example:
        runner = ClaudeRunner()

        # Simple execution
        result = await runner.run_phase(
            phase_dir=Path("/project/phases/01-foundation"),
            model="claude-3-opus"
        )

        # With live output streaming
        async def on_output(stream: str, line: str):
            print(f"[{stream}] {line}")

        result = await runner.run_phase_streaming(
            phase_dir=Path("/project/phases/01-foundation"),
            on_output=on_output
        )
    """

    DEFAULT_CLAUDE_CMD = "/home/aiuser01/.nvm/versions/node/v20.19.6/bin/claude"
    DEFAULT_TIMEOUT = 1800  # 30 minutes
    DEFAULT_VENV_PATH = Path("/home/aiuser01/helix-v4/.venv")

    def __init__(
        self,
        claude_cmd: str | None = None,
        llm_client: LLMClient | None = None,
        use_stdbuf: bool = True,
        venv_path: Path | None = None,
    ) -> None:
        """Initialize the ClaudeRunner.

        Args:
            claude_cmd: Path to the Claude Code CLI executable.
                       Defaults to "claude" (uses PATH).
            llm_client: Optional LLMClient for model resolution.
            use_stdbuf: Whether to use stdbuf for line buffering (default True).
            venv_path: Path to the Python virtualenv. Defaults to helix's .venv.
                      Set to None to disable virtualenv PATH injection.
        """
        # Ensure NVM node is in PATH for Claude CLI
        nvm_path = "/home/aiuser01/.nvm/versions/node/v20.19.6/bin"
        if nvm_path not in os.environ.get("PATH", ""):
            os.environ["PATH"] = f"{nvm_path}:{os.environ.get('PATH', '')}"

        self.claude_cmd = claude_cmd or self.DEFAULT_CLAUDE_CMD
        self.llm_client = llm_client or LLMClient()
        self.use_stdbuf = use_stdbuf and self._check_stdbuf_available()
        self.venv_path = venv_path if venv_path is not None else self.DEFAULT_VENV_PATH

    def _check_stdbuf_available(self) -> bool:
        """Check if stdbuf is available on the system."""
        return shutil.which("stdbuf") is not None

    def _get_venv_env(self) -> dict[str, str]:
        """Get environment variables with virtualenv activated.

        ADR-030 Fix 1: This method ensures Python tools like pytest
        are accessible in Claude Code bash sessions by prepending
        the virtualenv's bin directory to PATH.

        Returns:
            Dictionary with PATH and VIRTUAL_ENV set for the virtualenv.
        """
        env: dict[str, str] = {}

        if self.venv_path and self.venv_path.exists():
            venv_bin = self.venv_path / "bin"
            if venv_bin.exists():
                current_path = os.environ.get("PATH", "")
                # Prepend venv bin to PATH (before other entries)
                env["PATH"] = f"{venv_bin}:{current_path}"
                env["VIRTUAL_ENV"] = str(self.venv_path)

        return env

    def _verify_pytest_available(self, env: dict[str, str]) -> None:
        """Verify that pytest is accessible in the environment.

        ADR-030 Fix 1: Provides a clear error message if pytest
        cannot be found, helping diagnose PATH issues.

        Args:
            env: Environment dictionary to use for the check.

        Raises:
            EnvironmentError: If pytest is not found in PATH.
        """
        merged_env = {**os.environ, **env}
        result = subprocess.run(
            ["which", "pytest"],
            env=merged_env,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            venv_info = f"at {self.venv_path}" if self.venv_path else "(not configured)"
            raise EnvironmentError(
                f"pytest not found in PATH. "
                f"Ensure virtualenv {venv_info} is valid and contains pytest. "
                f"Current PATH: {merged_env.get('PATH', 'not set')}"
            )

    def _build_command(self, extra_args: list[str] | None = None) -> list[str]:
        """Build the Claude CLI command with optional stdbuf wrapper.

        Args:
            extra_args: Additional arguments for Claude CLI.

        Returns:
            Command list ready for subprocess execution.
        """
        cmd = []

        # Add stdbuf for line buffering if available
        if self.use_stdbuf:
            cmd.extend(["stdbuf", "-oL", "-eL"])

        cmd.extend([
            self.claude_cmd,
            "--print",
            "--dangerously-skip-permissions",
        ])

        if extra_args:
            cmd.extend(extra_args)

        return cmd

    async def run_phase(
        self,
        phase_dir: Path,
        model: str | None = None,
        prompt: str | None = None,
        timeout: int | None = None,
        env_overrides: dict[str, str] | None = None,
        verify_pytest: bool = False,
    ) -> ClaudeResult:
        """Run Claude Code CLI for a phase (buffered output).

        For live streaming output, use run_phase_streaming() instead.

        Args:
            phase_dir: Path to the phase directory.
            model: Optional model spec to use.
            prompt: Optional initial prompt. Defaults to reading CLAUDE.md.
            timeout: Optional timeout in seconds.
            env_overrides: Optional environment variable overrides.
            verify_pytest: If True, verify pytest is available before running.

        Returns:
            ClaudeResult with execution details.
        """
        import time

        start_time = time.time()

        env = self.get_claude_env(model)
        if env_overrides:
            env.update(env_overrides)

        # ADR-030 Fix 1: Optionally verify pytest is available
        if verify_pytest:
            try:
                self._verify_pytest_available(env)
            except EnvironmentError as e:
                duration = time.time() - start_time
                return ClaudeResult(
                    success=False,
                    exit_code=-1,
                    stdout="",
                    stderr=str(e),
                    duration_seconds=duration,
                )

        if prompt is None:
            claude_md = phase_dir / "CLAUDE.md"
            if claude_md.exists():
                prompt = "Read CLAUDE.md and execute all tasks described there."
            else:
                prompt = "Execute the phase tasks as defined in the spec."

        cmd = self._build_command()

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

    async def run_phase_streaming(
        self,
        phase_dir: Path,
        on_output: OutputCallback,
        model: str | None = None,
        prompt: str | None = None,
        timeout: int | None = None,
        env_overrides: dict[str, str] | None = None,
        verify_pytest: bool = False,
    ) -> ClaudeResult:
        """Run Claude Code CLI with live output streaming.

        This method streams output line-by-line as it becomes available,
        calling the on_output callback for each line.

        Args:
            phase_dir: Path to the phase directory.
            on_output: Async callback function(stream, line) for output.
            model: Optional model spec to use.
            prompt: Optional initial prompt.
            timeout: Optional timeout in seconds.
            env_overrides: Optional environment variable overrides.
            verify_pytest: If True, verify pytest is available before running.

        Returns:
            ClaudeResult with execution details.
        """
        import time

        start_time = time.time()

        env = self.get_claude_env(model)
        if env_overrides:
            env.update(env_overrides)

        # ADR-030 Fix 1: Optionally verify pytest is available
        if verify_pytest:
            try:
                self._verify_pytest_available(env)
            except EnvironmentError as e:
                duration = time.time() - start_time
                return ClaudeResult(
                    success=False,
                    exit_code=-1,
                    stdout="",
                    stderr=str(e),
                    duration_seconds=duration,
                )

        if prompt is None:
            claude_md = phase_dir / "CLAUDE.md"
            if claude_md.exists():
                prompt = "Read CLAUDE.md and execute all tasks described there."
            else:
                prompt = "Execute the phase tasks as defined in the spec."

        cmd = self._build_command()

        stdout_lines: list[str] = []
        stderr_lines: list[str] = []

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=phase_dir,
                env={**os.environ, **env},
            )

            # Send prompt to stdin
            if process.stdin:
                process.stdin.write(prompt.encode("utf-8"))
                await process.stdin.drain()
                process.stdin.close()
                await process.stdin.wait_closed()

            async def read_stream(
                stream: asyncio.StreamReader | None,
                stream_name: str,
                lines_list: list[str],
            ) -> None:
                """Read from stream line by line."""
                if stream is None:
                    return
                while True:
                    try:
                        line_bytes = await asyncio.wait_for(
                            stream.readline(),
                            timeout=1.0  # Check every second for overall timeout
                        )
                        if not line_bytes:
                            break
                        line = line_bytes.decode("utf-8", errors="replace").rstrip("\n\r")
                        lines_list.append(line)
                        await on_output(stream_name, line)
                    except asyncio.TimeoutError:
                        # Check if process is still running
                        if process.returncode is not None:
                            break
                        # Check overall timeout
                        if time.time() - start_time > (timeout or self.DEFAULT_TIMEOUT):
                            raise asyncio.TimeoutError("Overall timeout exceeded")

            # Read stdout and stderr concurrently
            await asyncio.gather(
                read_stream(process.stdout, "stdout", stdout_lines),
                read_stream(process.stderr, "stderr", stderr_lines),
            )

            # Wait for process to complete
            await process.wait()

            stdout = "\n".join(stdout_lines)
            stderr = "\n".join(stderr_lines)
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
            # Kill the process on timeout
            if process and process.returncode is None:
                process.kill()
                await process.wait()

            duration = time.time() - start_time
            return ClaudeResult(
                success=False,
                exit_code=-1,
                stdout="\n".join(stdout_lines),
                stderr=f"Timeout after {timeout or self.DEFAULT_TIMEOUT} seconds\n" + "\n".join(stderr_lines),
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
                stdout="\n".join(stdout_lines),
                stderr=str(e),
                duration_seconds=duration,
            )

    def get_claude_env(self, model_spec: str | None = None) -> dict[str, str]:
        """Get environment variables for Claude CLI execution.

        ADR-030 Fix 1: Now includes Python virtualenv in PATH to ensure
        pytest and other Python tools are accessible in bash sessions.

        Args:
            model_spec: Optional model spec to configure.

        Returns:
            Dictionary of environment variables to set.
        """
        # Include nvm node in PATH so claude CLI can find node
        nvm_bin = "/home/aiuser01/.nvm/versions/node/v20.19.6/bin"
        current_path = os.environ.get("PATH", "")
        if nvm_bin not in current_path:
            current_path = f"{nvm_bin}:{current_path}"

        env: dict[str, str] = {
            "PATH": current_path,
        }

        # ADR-030 Fix 1: Add virtualenv to PATH for pytest access
        venv_env = self._get_venv_env()
        if venv_env:
            # Merge venv PATH with existing PATH (venv takes precedence)
            if "PATH" in venv_env:
                env["PATH"] = f"{venv_env['PATH'].split(':')[0]}:{env['PATH']}"
            if "VIRTUAL_ENV" in venv_env:
                env["VIRTUAL_ENV"] = venv_env["VIRTUAL_ENV"]

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
        on_output: OutputCallback | None = None,
        **kwargs: Any,
    ) -> ClaudeResult:
        """Run Claude CLI with automatic retries.

        Args:
            phase_dir: Path to the phase directory.
            model: Optional model spec to use.
            max_retries: Maximum number of retry attempts.
            retry_delay: Delay between retries in seconds.
            on_output: Optional callback for live streaming.
            **kwargs: Additional arguments for run_phase.

        Returns:
            ClaudeResult from the successful run or last attempt.
        """
        last_result: ClaudeResult | None = None

        for attempt in range(max_retries + 1):
            if on_output:
                result = await self.run_phase_streaming(
                    phase_dir, on_output, model, **kwargs
                )
            else:
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
            env = self.get_claude_env()
            process = await asyncio.create_subprocess_exec(
                self.claude_cmd,
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, **env},
            )
            await asyncio.wait_for(process.communicate(), timeout=10.0)
            return process.returncode == 0
        except (FileNotFoundError, asyncio.TimeoutError):
            return False

    async def check_pytest_available(self) -> bool:
        """Check if pytest is available in the configured environment.

        ADR-030 Fix 1: Convenience method to verify pytest accessibility.

        Returns:
            True if pytest is found in PATH with virtualenv.
        """
        try:
            env = self.get_claude_env()
            self._verify_pytest_available(env)
            return True
        except EnvironmentError:
            return False
