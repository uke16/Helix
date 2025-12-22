"""
Agentic Meeting Orchestration for HELIX v4.

This module orchestrates "Agentic Meetings" with domain experts to analyze
user requests and generate project specifications.

The meeting process has 4 phases:
1. Request Analysis: Meta-Consultant recognizes keywords, selects experts
2. Expert Analysis: Each expert analyzes (parallel) and writes analysis.json
3. Synthesis: Meta-Consultant combines analyses, resolves conflicts
4. Output: Generates spec.yaml, phases.yaml, quality-gates.yaml
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# Note: Import from helix package when running in production
# from helix.llm_client import LLMClient
# For now, we define a protocol for type hints


@dataclass
class ExpertSelection:
    """Result of the expert selection phase."""

    experts: list[str]
    questions: dict[str, str]
    reasoning: str


@dataclass
class Analysis:
    """Analysis result from a single domain expert."""

    domain: str
    findings: list[str]
    requirements: list[str]
    constraints: list[str]
    recommendations: list[str]
    dependencies: list[str]
    open_questions: list[str]


@dataclass
class Synthesis:
    """Synthesized result from all expert analyses."""

    combined_requirements: list[str]
    conflicts_resolved: list[str]
    open_questions: list[str]
    recommended_phases: list[str]
    expert_contributions: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class MeetingResult:
    """Final result of a consultant meeting."""

    phases: dict[str, Any]
    transcript: str
    experts_consulted: list[str]
    duration_seconds: float
    # Optional fields
    spec: dict[str, Any] | None = None  # Deprecated, use ADR instead
    quality_gates: dict[str, Any] | None = None
    adr_path: Path | None = None  # Path to generated ADR file


class ConsultantMeeting:
    """
    Orchestrates agentic meetings with domain experts.

    The ConsultantMeeting class coordinates the entire meeting process,
    from analyzing the user request to generating the final output files.

    Args:
        llm_client: The LLM client for making AI calls.
        expert_manager: Manager for domain expert configurations.
    """

    def __init__(self, llm_client: Any, expert_manager: Any) -> None:
        """Initialize the consultant meeting.

        Args:
            llm_client: LLM client instance for AI interactions.
            expert_manager: ExpertManager instance for expert handling.
        """
        self.llm_client = llm_client
        self.expert_manager = expert_manager
        self._transcript_lines: list[str] = []

    def _log(self, message: str) -> None:
        """Add a message to the meeting transcript.

        Args:
            message: The message to log.
        """
        timestamp = time.strftime("%H:%M:%S")
        self._transcript_lines.append(f"[{timestamp}] {message}")

    async def run(self, project_dir: Path, user_request: str) -> MeetingResult:
        """Run a complete consultant meeting.

        This method orchestrates all 4 phases of the meeting:
        1. Request analysis and expert selection
        2. Parallel expert analyses
        3. Synthesis of all analyses
        4. Output generation

        Args:
            project_dir: The project directory for output files.
            user_request: The original user request to analyze.

        Returns:
            MeetingResult containing all generated specifications.
        """
        start_time = time.time()
        self._transcript_lines = []

        self._log("=== HELIX v4 Consultant Meeting Started ===")
        self._log(f"Project Directory: {project_dir}")
        self._log(f"User Request: {user_request[:200]}...")

        # Setup meeting directory structure
        meeting_dir = project_dir / "meeting"
        await self._setup_meeting_directories(meeting_dir)

        # Save original request
        input_dir = project_dir / "input"
        input_dir.mkdir(parents=True, exist_ok=True)
        (input_dir / "request.md").write_text(user_request, encoding="utf-8")

        # Phase 1: Analyze request and select experts
        self._log("\n--- Phase 1: Request Analysis & Expert Selection ---")
        selection = await self.analyze_request(user_request)
        self._log(f"Selected experts: {', '.join(selection.experts)}")
        self._log(f"Reasoning: {selection.reasoning}")

        # Save selection result
        selection_dir = meeting_dir / "phase-1-selection"
        selection_dir.mkdir(parents=True, exist_ok=True)
        (selection_dir / "expert-selection.json").write_text(
            json.dumps({
                "experts": selection.experts,
                "questions": selection.questions,
                "reasoning": selection.reasoning
            }, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

        # Phase 2: Run expert analyses
        self._log("\n--- Phase 2: Expert Analyses ---")
        analyses = await self.run_expert_analyses(
            selection.experts,
            user_request,
            selection.questions,
            meeting_dir / "phase-2-analysis"
        )
        for expert_id, analysis in analyses.items():
            self._log(f"Expert '{expert_id}' provided {len(analysis.findings)} findings")

        # Phase 3: Synthesize
        self._log("\n--- Phase 3: Synthesis ---")
        synthesis = await self.synthesize(analyses)
        self._log(f"Combined {len(synthesis.combined_requirements)} requirements")
        self._log(f"Resolved {len(synthesis.conflicts_resolved)} conflicts")

        # Save synthesis result
        synthesis_dir = meeting_dir / "phase-3-synthesis"
        synthesis_dir.mkdir(parents=True, exist_ok=True)
        (synthesis_dir / "synthesis.json").write_text(
            json.dumps({
                "combined_requirements": synthesis.combined_requirements,
                "conflicts_resolved": synthesis.conflicts_resolved,
                "open_questions": synthesis.open_questions,
                "recommended_phases": synthesis.recommended_phases
            }, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

        # Phase 4: Generate output
        self._log("\n--- Phase 4: Output Generation ---")
        result = await self.generate_output(
            synthesis,
            analyses,
            selection.experts,
            user_request,
            project_dir
        )

        # Calculate duration
        duration = time.time() - start_time
        result.duration_seconds = duration
        result.transcript = "\n".join(self._transcript_lines)

        # Save transcript
        logs_dir = project_dir / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        (logs_dir / "meeting-transcript.md").write_text(
            result.transcript,
            encoding="utf-8"
        )

        self._log(f"\n=== Meeting Completed in {duration:.2f}s ===")

        return result

    async def _setup_meeting_directories(self, meeting_dir: Path) -> None:
        """Create the meeting directory structure.

        Args:
            meeting_dir: Base meeting directory.
        """
        directories = [
            meeting_dir / "phase-1-selection",
            meeting_dir / "phase-2-analysis",
            meeting_dir / "phase-3-synthesis",
        ]
        for d in directories:
            d.mkdir(parents=True, exist_ok=True)

    async def analyze_request(self, request: str) -> ExpertSelection:
        """Analyze the user request and select appropriate domain experts.

        This method uses the LLM to analyze the request and determine
        which domain experts should be consulted.

        Args:
            request: The user request to analyze.

        Returns:
            ExpertSelection with selected experts and their questions.
        """
        # Get available experts from the manager
        available_experts = self.expert_manager.load_experts()

        # First, use keyword-based selection as a baseline
        keyword_selected = self.expert_manager.select_experts(request)

        # Build expert descriptions for the prompt
        expert_descriptions = "\n".join([
            f"- {exp.id}: {exp.name} - {exp.description} (triggers: {', '.join(exp.triggers)})"
            for exp in available_experts.values()
        ])

        prompt = f"""Analyze the following user request and determine which domain experts should be consulted.

Available Experts:
{expert_descriptions}

User Request:
{request}

Based on keyword matching, these experts were pre-selected: {keyword_selected}

Please analyze the request and:
1. Confirm or adjust the expert selection
2. Formulate a specific question for each selected expert
3. Provide reasoning for your selection

Respond in JSON format:
{{
    "experts": ["expert_id1", "expert_id2"],
    "questions": {{
        "expert_id1": "Specific question for this expert...",
        "expert_id2": "Specific question for this expert..."
    }},
    "reasoning": "Explanation of why these experts were selected..."
}}"""

        try:
            response = await self.llm_client.complete(prompt)
            result = json.loads(response)

            return ExpertSelection(
                experts=result.get("experts", keyword_selected),
                questions=result.get("questions", {}),
                reasoning=result.get("reasoning", "Keyword-based selection")
            )
        except (json.JSONDecodeError, AttributeError):
            # Fallback to keyword-based selection
            return ExpertSelection(
                experts=keyword_selected,
                questions={exp: f"Analyze the request from your {exp} perspective"
                          for exp in keyword_selected},
                reasoning="Fallback to keyword-based selection"
            )

    async def run_expert_analyses(
        self,
        experts: list[str],
        request: str,
        questions: dict[str, str],
        analysis_dir: Path
    ) -> dict[str, Analysis]:
        """Run analyses for all selected experts in parallel.

        Each expert analyzes the request from their domain perspective
        and produces an analysis.json file.

        Args:
            experts: List of expert IDs to consult.
            request: The user request to analyze.
            questions: Specific questions for each expert.
            analysis_dir: Directory for storing analysis outputs.

        Returns:
            Dictionary mapping expert IDs to their Analysis results.
        """
        async def analyze_with_expert(expert_id: str) -> tuple[str, Analysis]:
            """Run analysis for a single expert."""
            expert_config = self.expert_manager.load_experts().get(expert_id)
            if not expert_config:
                return expert_id, Analysis(
                    domain=expert_id,
                    findings=["Expert not found"],
                    requirements=[],
                    constraints=[],
                    recommendations=[],
                    dependencies=[],
                    open_questions=[]
                )

            # Setup expert directory
            expert_dir = analysis_dir / f"{expert_id}-expert"
            expert_dir.mkdir(parents=True, exist_ok=True)

            # Generate CLAUDE.md for this expert
            question = questions.get(expert_id, f"Analyze from {expert_id} perspective")
            claude_md = self.expert_manager.generate_expert_claude_md(
                expert_config, question
            )
            (expert_dir / "CLAUDE.md").write_text(claude_md, encoding="utf-8")

            # Run expert analysis via LLM
            prompt = f"""You are a {expert_config.name} expert.
Your expertise: {expert_config.description}
Your skills: {', '.join(expert_config.skills)}

Analyze the following request from your domain perspective:

User Request:
{request}

Specific Question for You:
{question}

Provide your analysis in JSON format:
{{
    "domain": "{expert_id}",
    "findings": ["Key observations from your domain perspective..."],
    "requirements": ["Technical requirements you identified..."],
    "constraints": ["Constraints or limitations to consider..."],
    "recommendations": ["Your expert recommendations..."],
    "dependencies": ["Dependencies on other systems or components..."],
    "open_questions": ["Questions that need clarification..."]
}}"""

            try:
                response = await self.llm_client.complete(prompt)
                result = json.loads(response)

                analysis = Analysis(
                    domain=result.get("domain", expert_id),
                    findings=result.get("findings", []),
                    requirements=result.get("requirements", []),
                    constraints=result.get("constraints", []),
                    recommendations=result.get("recommendations", []),
                    dependencies=result.get("dependencies", []),
                    open_questions=result.get("open_questions", [])
                )
            except (json.JSONDecodeError, AttributeError):
                analysis = Analysis(
                    domain=expert_id,
                    findings=[f"Analysis pending for {expert_id}"],
                    requirements=[],
                    constraints=[],
                    recommendations=[],
                    dependencies=[],
                    open_questions=["LLM response parsing failed"]
                )

            # Save analysis output
            output_dir = expert_dir / "output"
            output_dir.mkdir(parents=True, exist_ok=True)
            (output_dir / "analysis.json").write_text(
                json.dumps({
                    "domain": analysis.domain,
                    "findings": analysis.findings,
                    "requirements": analysis.requirements,
                    "constraints": analysis.constraints,
                    "recommendations": analysis.recommendations,
                    "dependencies": analysis.dependencies,
                    "open_questions": analysis.open_questions
                }, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )

            return expert_id, analysis

        # Run all expert analyses in parallel
        tasks = [analyze_with_expert(exp_id) for exp_id in experts]
        results = await asyncio.gather(*tasks)

        return dict(results)

    async def synthesize(self, analyses: dict[str, Analysis]) -> Synthesis:
        """Synthesize all expert analyses into a coherent result.

        The Meta-Consultant combines all expert analyses, resolves
        conflicts, and produces a unified synthesis.

        Args:
            analyses: Dictionary of expert analyses.

        Returns:
            Synthesis combining all expert insights.
        """
        # Collect all inputs
        all_requirements: list[str] = []
        all_constraints: list[str] = []
        all_recommendations: list[str] = []
        all_dependencies: list[str] = []
        all_open_questions: list[str] = []
        expert_contributions: dict[str, list[str]] = {}

        for expert_id, analysis in analyses.items():
            all_requirements.extend(analysis.requirements)
            all_constraints.extend(analysis.constraints)
            all_recommendations.extend(analysis.recommendations)
            all_dependencies.extend(analysis.dependencies)
            all_open_questions.extend(analysis.open_questions)
            expert_contributions[expert_id] = analysis.findings

        # Build synthesis prompt
        analyses_summary = "\n\n".join([
            f"=== {exp_id.upper()} Expert ===\n"
            f"Findings: {', '.join(a.findings)}\n"
            f"Requirements: {', '.join(a.requirements)}\n"
            f"Constraints: {', '.join(a.constraints)}\n"
            f"Recommendations: {', '.join(a.recommendations)}"
            for exp_id, a in analyses.items()
        ])

        prompt = f"""As Meta-Consultant, synthesize the following expert analyses into a coherent project plan.

Expert Analyses:
{analyses_summary}

Your task:
1. Combine all requirements, removing duplicates
2. Identify and resolve any conflicts between experts
3. Consolidate open questions
4. Recommend implementation phases

Respond in JSON format:
{{
    "combined_requirements": ["Unique, prioritized requirements..."],
    "conflicts_resolved": ["Description of conflicts and how they were resolved..."],
    "open_questions": ["Remaining questions that need user clarification..."],
    "recommended_phases": ["Phase 1: ...", "Phase 2: ...", ...]
}}"""

        try:
            response = await self.llm_client.complete(prompt)
            result = json.loads(response)

            return Synthesis(
                combined_requirements=result.get("combined_requirements", all_requirements),
                conflicts_resolved=result.get("conflicts_resolved", []),
                open_questions=result.get("open_questions", all_open_questions),
                recommended_phases=result.get("recommended_phases", []),
                expert_contributions=expert_contributions
            )
        except (json.JSONDecodeError, AttributeError):
            # Fallback synthesis
            return Synthesis(
                combined_requirements=list(set(all_requirements)),
                conflicts_resolved=[],
                open_questions=list(set(all_open_questions)),
                recommended_phases=["Phase 1: Implementation"],
                expert_contributions=expert_contributions
            )

    async def generate_output(
        self,
        synthesis: Synthesis,
        analyses: dict[str, Analysis],
        experts_consulted: list[str],
        original_request: str,
        project_dir: Path
    ) -> MeetingResult:
        """Generate the final output files from the synthesis.

        Creates spec.yaml, phases.yaml, and quality-gates.yaml files
        based on the synthesized meeting results.

        Args:
            synthesis: The synthesized analysis result.
            analyses: Individual expert analyses.
            experts_consulted: List of consulted expert IDs.
            original_request: The original user request.
            project_dir: Project directory for output files.

        Returns:
            MeetingResult with all generated specifications.
        """
        output_dir = project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate spec.yaml
        spec = {
            "version": "1.0",
            "name": "generated-project",
            "description": original_request[:200],
            "requirements": synthesis.combined_requirements,
            "constraints": [],
            "experts_consulted": experts_consulted,
            "open_questions": synthesis.open_questions
        }

        # Add constraints from all analyses
        for analysis in analyses.values():
            spec["constraints"].extend(analysis.constraints)
        spec["constraints"] = list(set(spec["constraints"]))

        # Generate phases.yaml
        phases = {
            "version": "1.0",
            "phases": []
        }

        for i, phase_desc in enumerate(synthesis.recommended_phases, 1):
            phases["phases"].append({
                "id": f"phase-{i:02d}",
                "name": phase_desc,
                "description": phase_desc,
                "dependencies": [f"phase-{i-1:02d}"] if i > 1 else [],
                "outputs": []
            })

        # Generate quality-gates.yaml
        quality_gates = {
            "version": "1.0",
            "gates": [
                {
                    "id": "gate-01",
                    "name": "Requirements Review",
                    "type": "manual",
                    "criteria": ["All requirements documented", "Expert analyses complete"]
                },
                {
                    "id": "gate-02",
                    "name": "Implementation Review",
                    "type": "automated",
                    "criteria": ["All tests pass", "No critical issues"]
                },
                {
                    "id": "gate-03",
                    "name": "Final Acceptance",
                    "type": "manual",
                    "criteria": ["User acceptance", "Documentation complete"]
                }
            ]
        }

        # Write output files
        (output_dir / "spec.yaml").write_text(
            yaml.dump(spec, allow_unicode=True, default_flow_style=False, sort_keys=False),
            encoding="utf-8"
        )
        self._log(f"Generated: {output_dir / 'spec.yaml'}")

        (output_dir / "phases.yaml").write_text(
            yaml.dump(phases, allow_unicode=True, default_flow_style=False, sort_keys=False),
            encoding="utf-8"
        )
        self._log(f"Generated: {output_dir / 'phases.yaml'}")

        (output_dir / "quality-gates.yaml").write_text(
            yaml.dump(quality_gates, allow_unicode=True, default_flow_style=False, sort_keys=False),
            encoding="utf-8"
        )
        self._log(f"Generated: {output_dir / 'quality-gates.yaml'}")

        return MeetingResult(
            spec=spec,
            phases=phases,
            quality_gates=quality_gates,
            transcript="",  # Will be set by caller
            experts_consulted=experts_consulted,
            duration_seconds=0.0  # Will be set by caller
        )
