"""Phase definition loader for HELIX v4.

Loads and validates phases.yaml configuration files.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from helix.config.paths import PathConfig


@dataclass
class PhaseConfig:
    """Configuration for a single phase in the workflow.

    Attributes:
        id: Unique identifier for the phase (e.g., "01-foundation").
        name: Human-readable name of the phase.
        type: Phase type - one of: meeting, development, review, documentation, test.
        config: Additional phase-specific configuration.
        input: Expected input files/artifacts for this phase.
        output: Expected output files/artifacts from this phase.
        quality_gate: Quality gate configuration for this phase.
    """
    id: str
    name: str
    type: str
    config: dict[str, Any] = field(default_factory=dict)
    input: dict[str, Any] = field(default_factory=dict)
    output: dict[str, Any] = field(default_factory=dict)
    quality_gate: dict[str, Any] = field(default_factory=dict)


class PhaseLoader:
    """Loads and validates phase definitions from phases.yaml.

    The PhaseLoader reads project phase configurations and converts them
    to PhaseConfig objects for use by the Orchestrator.

    Example:
        loader = PhaseLoader()
        phases = loader.load_phases(Path("/path/to/project"))
        for phase in phases:
            print(f"Phase {phase.id}: {phase.name}")
    """

    VALID_PHASE_TYPES = {"meeting", "consultant", "development", "review", "documentation", "test"}

    def __init__(self, templates_dir: Path | None = None) -> None:
        """Initialize the PhaseLoader.

        Args:
            templates_dir: Optional directory containing phase templates.
                          Defaults to PathConfig.TEMPLATES_PHASES.
        """
        self.templates_dir = templates_dir or PathConfig.TEMPLATES_PHASES

    def load_phases(self, project_dir: Path) -> list[PhaseConfig]:
        """Load all phases from a project's phases.yaml.

        Args:
            project_dir: Path to the project directory containing phases.yaml.

        Returns:
            List of PhaseConfig objects in execution order.

        Raises:
            FileNotFoundError: If phases.yaml does not exist.
            ValueError: If phases.yaml is invalid.
        """
        phases_file = project_dir / "phases.yaml"

        if not phases_file.exists():
            raise FileNotFoundError(f"phases.yaml not found in {project_dir}")

        with open(phases_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not data:
            raise ValueError(f"phases.yaml is empty or invalid: {phases_file}")

        phases_data = data.get("phases", [])
        if not phases_data:
            raise ValueError("No phases defined in phases.yaml")

        project_type = data.get("project_type")
        if project_type:
            phases_data = self._apply_template(project_type, phases_data)

        return [self._parse_phase(phase_data) for phase_data in phases_data]

    def _apply_template(
        self, project_type: str, phases_data: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Apply project type template defaults to phases.

        Args:
            project_type: Type of project (e.g., "python-cli", "web-app").
            phases_data: Raw phase data from phases.yaml.

        Returns:
            Phase data with template defaults applied.
        """
        template_file = self.templates_dir / f"{project_type}.yaml"

        if not template_file.exists():
            return phases_data

        with open(template_file, "r", encoding="utf-8") as f:
            template_data = yaml.safe_load(f) or {}

        template_phases = {p["id"]: p for p in template_data.get("phases", [])}

        result = []
        for phase in phases_data:
            phase_id = phase.get("id", "")
            if phase_id in template_phases:
                merged = {**template_phases[phase_id], **phase}
                result.append(merged)
            else:
                result.append(phase)

        return result

    def _parse_phase(self, phase_data: dict[str, Any]) -> PhaseConfig:
        """Parse a single phase configuration.

        Args:
            phase_data: Raw phase data dictionary.

        Returns:
            PhaseConfig object.

        Raises:
            ValueError: If required fields are missing or phase type is invalid.
        """
        phase_id = phase_data.get("id")
        if not phase_id:
            raise ValueError("Phase is missing required 'id' field")

        name = phase_data.get("name", phase_id)
        phase_type = phase_data.get("type", "development")

        if phase_type not in self.VALID_PHASE_TYPES:
            raise ValueError(
                f"Invalid phase type '{phase_type}' for phase '{phase_id}'. "
                f"Valid types: {self.VALID_PHASE_TYPES}"
            )

        return PhaseConfig(
            id=phase_id,
            name=name,
            type=phase_type,
            config=phase_data.get("config", {}),
            input=phase_data.get("input", {}),
            output=phase_data.get("output", {}),
            quality_gate=phase_data.get("quality_gate", {}),
        )

    def get_phase_dir(self, project_dir: Path, phase_config: PhaseConfig) -> Path:
        """Get the directory path for a specific phase.

        Args:
            project_dir: Path to the project directory.
            phase_config: The phase configuration.

        Returns:
            Path to the phase directory.
        """
        return project_dir / "phases" / phase_config.id
