"""Planning Agent for complex projects.

The Planning Agent analyzes project scope and dynamically
generates 1-5 phases based on complexity and requirements.

Example:
    agent = PlanningAgent(max_phases=5)
    plan = await agent.analyze_and_plan(
        project_description="Add authentication system",
        adr_content=adr_text,
    )
    print(f"Generated {len(plan.phases)} phases")
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import json
import yaml

from helix.claude_runner import ClaudeRunner


@dataclass
class PlannedPhase:
    """A planned phase from the Planning Agent.

    Attributes:
        id: Unique phase identifier (e.g., "dev-1", "dev-2").
        name: Human-readable phase name.
        type: Phase type (development, documentation, test, research).
        description: What this phase accomplishes.
        estimated_sessions: Estimated Claude Code sessions (1-2).
        dependencies: IDs of phases this depends on.
    """

    id: str
    name: str
    type: str
    description: str
    estimated_sessions: int = 1
    dependencies: list[str] = field(default_factory=list)


@dataclass
class ProjectPlan:
    """Complete plan from the Planning Agent.

    Attributes:
        phases: List of planned phases.
        feasibility_needed: Whether a feasibility study is recommended.
        total_estimated_sessions: Sum of all phase session estimates.
        reasoning: Why this plan was chosen.
    """

    phases: list[PlannedPhase]
    feasibility_needed: bool = False
    total_estimated_sessions: int = 0
    reasoning: str = ""

    def __post_init__(self):
        """Calculate total sessions if not provided."""
        if self.total_estimated_sessions == 0:
            self.total_estimated_sessions = sum(
                p.estimated_sessions for p in self.phases
            )


class PlanningAgent:
    """Generates dynamic phases for complex projects.

    The agent analyzes the project scope and generates
    an appropriate number of phases (1-5). It uses a
    capable model (Sonnet) for reasoning about complexity.

    Attributes:
        max_phases: Maximum number of phases to generate.
        runner: ClaudeRunner for LLM execution.
    """

    PLANNING_PROMPT = '''You are a Planning Agent for HELIX projects.

## Project Description

{description}

## ADR Content (if available)

{adr_content}

## Your Task

Analyze this project and create a plan with 1-{max_phases} development phases.

### Guidelines

1. **Phase Sizing**: Each phase should be completable in 1-2 Claude Code sessions
2. **Complexity Assessment**:
   - Simple tasks: 1-2 phases
   - Medium complexity: 2-3 phases
   - High complexity: 3-5 phases
3. **Feasibility**: Recommend feasibility study if:
   - Requirements are unclear
   - Technical approach is uncertain
   - Integration with unknown systems
4. **Dependencies**: Order phases logically
   - Data layer before API layer
   - Core functionality before features
   - Implementation before tests

### Phase Types

- `development`: Code implementation
- `documentation`: Writing docs, updating CLAUDE.md
- `test`: Writing tests, E2E validation
- `research`: Investigation, feasibility study

### Output Format (YAML)

Output ONLY this YAML block, nothing else:

```yaml
feasibility_needed: false
reasoning: "Brief explanation of the plan"
phases:
  - id: dev-1
    name: "Data Layer Implementation"
    type: development
    description: "Implement data models and database interactions"
    estimated_sessions: 1
    dependencies: []
  - id: dev-2
    name: "API Layer"
    type: development
    description: "Build REST API endpoints"
    estimated_sessions: 2
    dependencies: [dev-1]
```

IMPORTANT: Output ONLY the YAML block. No additional text.
'''

    def __init__(self, max_phases: int = 5):
        """Initialize the Planning Agent.

        Args:
            max_phases: Maximum number of phases to generate (1-5).
        """
        self.max_phases = min(max_phases, 5)  # Cap at 5
        self.runner = ClaudeRunner()

    async def analyze_and_plan(
        self,
        project_description: str,
        adr_content: str | None = None,
        working_dir: Path | None = None,
    ) -> ProjectPlan:
        """Analyze project scope and generate phases.

        Uses an LLM to analyze the project description and ADR
        content to determine the appropriate number and type
        of development phases.

        Args:
            project_description: Description of the project.
            adr_content: Optional ADR document content.
            working_dir: Optional working directory for execution.

        Returns:
            ProjectPlan with generated phases.
        """
        prompt = self.PLANNING_PROMPT.format(
            description=project_description,
            adr_content=adr_content or "No ADR provided",
            max_phases=self.max_phases,
        )

        result = await self.runner.run_phase(
            phase_dir=working_dir or Path.cwd(),
            prompt=prompt,
            timeout=180,  # 3 minutes
            env_overrides={"CLAUDE_MODEL": "claude-sonnet-4-20250514"},
        )

        return self._parse_plan(result)

    def _parse_plan(self, claude_result: Any) -> ProjectPlan:
        """Parse Claude result into ProjectPlan.

        Extracts YAML from the Claude output and converts
        it into a structured ProjectPlan.

        Args:
            claude_result: Result from ClaudeRunner.

        Returns:
            Parsed ProjectPlan.
        """
        # Try to extract YAML from stdout
        stdout = claude_result.stdout or ""

        yaml_content = self._extract_yaml(stdout)
        if yaml_content:
            try:
                data = yaml.safe_load(yaml_content)
                return self._data_to_plan(data)
            except yaml.YAMLError:
                pass

        # Try JSON output
        if claude_result.output_json:
            return self._data_to_plan(claude_result.output_json)

        # Fallback: single generic phase
        return ProjectPlan(
            phases=[
                PlannedPhase(
                    id="dev-1",
                    name="Implementation",
                    type="development",
                    description="Implement the project requirements",
                    estimated_sessions=2,
                )
            ],
            feasibility_needed=False,
            reasoning="Fallback plan - could not parse agent output",
        )

    def _extract_yaml(self, text: str) -> str | None:
        """Extract YAML block from text.

        Looks for ```yaml ... ``` blocks in the text.

        Args:
            text: Text potentially containing YAML.

        Returns:
            YAML content or None.
        """
        yaml_start = text.find("```yaml")
        if yaml_start == -1:
            return None

        yaml_end = text.find("```", yaml_start + 7)
        if yaml_end == -1:
            return None

        return text[yaml_start + 7 : yaml_end].strip()

    def _data_to_plan(self, data: dict[str, Any]) -> ProjectPlan:
        """Convert parsed data to ProjectPlan.

        Args:
            data: Parsed YAML/JSON data.

        Returns:
            ProjectPlan instance.
        """
        phases = []
        for phase_data in data.get("phases", []):
            phases.append(
                PlannedPhase(
                    id=phase_data.get("id", f"dev-{len(phases)+1}"),
                    name=phase_data.get("name", "Unnamed Phase"),
                    type=phase_data.get("type", "development"),
                    description=phase_data.get("description", ""),
                    estimated_sessions=phase_data.get("estimated_sessions", 1),
                    dependencies=phase_data.get("dependencies", []),
                )
            )

        # Limit to max_phases
        phases = phases[: self.max_phases]

        return ProjectPlan(
            phases=phases,
            feasibility_needed=data.get("feasibility_needed", False),
            reasoning=data.get("reasoning", ""),
        )

    def estimate_complexity(self, description: str) -> str:
        """Quick complexity estimate without LLM call.

        Uses heuristics to estimate project complexity.

        Args:
            description: Project description.

        Returns:
            Complexity level: "low", "medium", or "high".
        """
        lower_desc = description.lower()

        # High complexity indicators
        high_indicators = [
            "refactor",
            "migrate",
            "redesign",
            "architecture",
            "distributed",
            "scalable",
            "integration",
            "multiple systems",
        ]

        # Medium complexity indicators
        medium_indicators = [
            "api",
            "database",
            "authentication",
            "authorization",
            "workflow",
            "pipeline",
        ]

        high_count = sum(1 for ind in high_indicators if ind in lower_desc)
        medium_count = sum(1 for ind in medium_indicators if ind in lower_desc)

        if high_count >= 2 or (high_count >= 1 and medium_count >= 2):
            return "high"
        elif medium_count >= 2 or high_count >= 1:
            return "medium"
        else:
            return "low"
