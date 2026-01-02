"""Central path configuration for HELIX.

ADR-035 Fix 7: Replaces hardcoded paths with a centralized configuration
that supports environment variable overrides.

This module provides:
- HELIX_ROOT: Base directory for the HELIX installation
- VENV_PATH: Path to the Python virtualenv
- CLAUDE_CMD: Path to the Claude CLI executable
- NVM_PATH: Path to the NVM node binaries

Environment Variables:
- HELIX_ROOT: Override the base HELIX directory
- HELIX_VENV: Override the virtualenv path
- CLAUDE_CMD: Override the Claude CLI path
- NVM_BIN: Override the NVM bin directory

Example:
    from helix.config.paths import PathConfig

    # Ensure Claude is accessible
    PathConfig.ensure_claude_path()

    # Get the Claude command
    runner = ClaudeRunner(claude_cmd=PathConfig.CLAUDE_CMD)
"""

import os
import shutil
from pathlib import Path
from typing import Optional


def _find_nvm_bin() -> Optional[str]:
    """Find NVM node bin directory with Claude CLI.

    Searches common locations for NVM-managed Node.js installations.
    Prefers versions that have Claude CLI installed.

    Returns:
        Path to NVM bin directory, or None if not found.
    """
    home = Path.home()
    nvm_base = home / ".nvm" / "versions" / "node"

    if nvm_base.exists():
        versions = sorted(nvm_base.iterdir(), reverse=True)

        # First pass: find version WITH claude CLI
        for version in versions:
            bin_path = version / "bin"
            if bin_path.exists() and (bin_path / "claude").exists():
                return str(bin_path)

        # Fallback: any version with node (claude may be elsewhere)
        for version in versions:
            bin_path = version / "bin"
            if bin_path.exists() and (bin_path / "node").exists():
                return str(bin_path)

    # Fallback: check if node is in PATH already
    node_path = shutil.which("node")
    if node_path:
        return str(Path(node_path).parent)

    return None


def _find_helix_root() -> Path:
    """Find the HELIX root directory.

    Looks for the root by walking up from this file's location
    until it finds a directory containing 'src/helix'.

    Returns:
        Path to the HELIX root directory.
    """
    # Start from this file's location
    current = Path(__file__).resolve()

    # Walk up until we find src/helix or hit root
    for _ in range(10):  # Limit iterations for safety
        parent = current.parent
        if (parent / "src" / "helix").exists():
            return parent
        if parent == current:
            # Reached filesystem root
            break
        current = parent

    # Fallback: assume standard layout
    # config/paths.py is in src/helix/config/
    # so root is 4 levels up
    return Path(__file__).parent.parent.parent.parent


class PathConfig:
    """Central path configuration with environment variable support.

    ADR-035 Fix 7: All paths are configurable via environment variables,
    with sensible defaults for the standard HELIX installation.

    Class Attributes:
        HELIX_ROOT: Base directory for HELIX (env: HELIX_ROOT)
        VENV_PATH: Python virtualenv path (env: HELIX_VENV)
        CLAUDE_CMD: Claude CLI executable path (env: CLAUDE_CMD)
        NVM_PATH: NVM node bin directory (env: NVM_BIN)

    Example:
        # Ensure paths are set up before running Claude
        PathConfig.ensure_claude_path()

        # Access configured paths
        runner = ClaudeRunner(
            claude_cmd=PathConfig.CLAUDE_CMD,
            venv_path=PathConfig.VENV_PATH,
        )
    """

    # HELIX root directory
    HELIX_ROOT: Path = Path(os.environ.get(
        "HELIX_ROOT",
        str(_find_helix_root())
    ))

    # Python virtualenv path
    VENV_PATH: Path = Path(os.environ.get(
        "HELIX_VENV",
        str(HELIX_ROOT / ".venv")
    ))

    # Claude CLI command/path
    CLAUDE_CMD: str = os.environ.get(
        "CLAUDE_CMD",
        shutil.which("claude") or "claude"
    )

    # NVM node bin directory
    NVM_PATH: Optional[str] = os.environ.get(
        "NVM_BIN",
        _find_nvm_bin()
    )

    # Sessions directory
    SESSIONS_PATH: Path = Path(os.environ.get(
        "HELIX_SESSIONS",
        str(HELIX_ROOT / "projects" / "sessions")
    ))

    # Templates directory
    TEMPLATES_PATH: Path = Path(os.environ.get(
        "HELIX_TEMPLATES",
        str(HELIX_ROOT / "templates")
    ))

    # Control scripts directory (for claude-wrapper.sh)
    CONTROL_PATH: Path = Path(os.environ.get(
        "HELIX_CONTROL",
        str(HELIX_ROOT / "control")
    ))

    # Config files
    DOMAIN_EXPERTS_CONFIG: Path = Path(os.environ.get(
        "HELIX_DOMAIN_EXPERTS_CONFIG",
        str(HELIX_ROOT / "config" / "domain-experts.yaml")
    ))

    LLM_PROVIDERS_CONFIG: Path = Path(os.environ.get(
        "HELIX_LLM_PROVIDERS_CONFIG",
        str(HELIX_ROOT / "config" / "llm-providers.yaml")
    ))

    # Skills directory
    SKILLS_DIR: Path = Path(os.environ.get(
        "HELIX_SKILLS_DIR",
        str(HELIX_ROOT / "skills")
    ))

    # Templates directory (alternative access - same as TEMPLATES_PATH)
    TEMPLATES_DIR: Path = TEMPLATES_PATH

    # Phases templates directory
    TEMPLATES_PHASES: Path = Path(os.environ.get(
        "HELIX_TEMPLATES_PHASES",
        str(TEMPLATES_PATH / "phases")
    ))

    @classmethod
    def ensure_claude_path(cls) -> None:
        """Add NVM to PATH if needed.

        ADR-035 Fix 8: Centralizes PATH setup that was previously
        duplicated in _run_consultant_streaming and _run_consultant.

        This method is idempotent - safe to call multiple times.
        """
        if cls.NVM_PATH and cls.NVM_PATH not in os.environ.get("PATH", ""):
            os.environ["PATH"] = f"{cls.NVM_PATH}:{os.environ.get('PATH', '')}"

    @classmethod
    def ensure_venv_path(cls) -> None:
        """Add virtualenv bin to PATH if needed.

        This enables Python tools like pytest to be accessible
        in subprocess calls.

        This method is idempotent - safe to call multiple times.
        """
        if cls.VENV_PATH.exists():
            venv_bin = str(cls.VENV_PATH / "bin")
            if venv_bin not in os.environ.get("PATH", ""):
                os.environ["PATH"] = f"{venv_bin}:{os.environ.get('PATH', '')}"

    @classmethod
    def get_claude_wrapper(cls) -> str:
        """Get the path to claude-wrapper.sh if it exists.

        Returns:
            Path to claude-wrapper.sh, or CLAUDE_CMD if wrapper doesn't exist.
        """
        wrapper = cls.CONTROL_PATH / "claude-wrapper.sh"
        if wrapper.exists():
            return str(wrapper)
        return cls.CLAUDE_CMD

    @classmethod
    def get_env_dict(cls) -> dict[str, str]:
        """Get environment variables for subprocess calls.

        Returns a dictionary suitable for use with subprocess.run()
        or asyncio.create_subprocess_exec().

        Returns:
            Dictionary with PATH, VIRTUAL_ENV, and other relevant vars.
        """
        env: dict[str, str] = {}

        # Build PATH with NVM and venv
        path_parts: list[str] = []

        if cls.NVM_PATH:
            path_parts.append(cls.NVM_PATH)

        if cls.VENV_PATH.exists():
            venv_bin = str(cls.VENV_PATH / "bin")
            path_parts.append(venv_bin)
            env["VIRTUAL_ENV"] = str(cls.VENV_PATH)

        # Add existing PATH
        current_path = os.environ.get("PATH", "")
        path_parts.append(current_path)

        env["PATH"] = ":".join(path_parts)

        return env

    @classmethod
    def validate(cls) -> dict[str, bool]:
        """Validate that all configured paths exist.

        Returns:
            Dictionary with path names as keys and existence as values.
        """
        return {
            "HELIX_ROOT": cls.HELIX_ROOT.exists(),
            "VENV_PATH": cls.VENV_PATH.exists(),
            "CLAUDE_CMD": shutil.which(cls.CLAUDE_CMD) is not None,
            "NVM_PATH": cls.NVM_PATH is not None and Path(cls.NVM_PATH).exists(),
            "SESSIONS_PATH": cls.SESSIONS_PATH.exists(),
            "TEMPLATES_PATH": cls.TEMPLATES_PATH.exists(),
            "CONTROL_PATH": cls.CONTROL_PATH.exists(),
            "DOMAIN_EXPERTS_CONFIG": cls.DOMAIN_EXPERTS_CONFIG.exists(),
            "LLM_PROVIDERS_CONFIG": cls.LLM_PROVIDERS_CONFIG.exists(),
            "SKILLS_DIR": cls.SKILLS_DIR.exists(),
            "TEMPLATES_PHASES": cls.TEMPLATES_PHASES.exists(),
        }

    @classmethod
    def info(cls) -> dict[str, str]:
        """Get information about current path configuration.

        Returns:
            Dictionary with path names and their current values.
        """
        return {
            "HELIX_ROOT": str(cls.HELIX_ROOT),
            "VENV_PATH": str(cls.VENV_PATH),
            "CLAUDE_CMD": cls.CLAUDE_CMD,
            "NVM_PATH": cls.NVM_PATH or "(not found)",
            "SESSIONS_PATH": str(cls.SESSIONS_PATH),
            "TEMPLATES_PATH": str(cls.TEMPLATES_PATH),
            "CONTROL_PATH": str(cls.CONTROL_PATH),
            "DOMAIN_EXPERTS_CONFIG": str(cls.DOMAIN_EXPERTS_CONFIG),
            "LLM_PROVIDERS_CONFIG": str(cls.LLM_PROVIDERS_CONFIG),
            "SKILLS_DIR": str(cls.SKILLS_DIR),
            "TEMPLATES_PHASES": str(cls.TEMPLATES_PHASES),
        }
