"""
Step Marker Validator.

Validates that LLM responses contain the required STEP marker
for tracking conversation flow state.

ADR-038: Deterministic LLM Response Enforcement
"""

import re
from typing import Optional

from .base import ResponseValidator, ValidationIssue


class StepMarkerValidator(ResponseValidator):
    """
    Validates that responses contain a valid STEP marker.

    The STEP marker format is: <!-- STEP: <step_name> -->
    where step_name is one of the valid steps.

    Valid steps:
        - what: Gathering what the user wants
        - why: Understanding the reason/motivation
        - constraints: Discussing constraints and limitations
        - generate: Generating the ADR/output
        - finalize: Finalizing the output
        - done: Conversation complete

    Example:
        validator = StepMarkerValidator()
        issues = validator.validate("Some response\\n<!-- STEP: generate -->", {})
        # issues == []  # Valid
    """

    # Pattern to match STEP markers (case insensitive for step name)
    PATTERN = r"<!--\s*STEP:\s*(\w+)\s*-->"

    # Valid step values
    VALID_STEPS = {"what", "why", "constraints", "generate", "finalize", "done"}

    @property
    def name(self) -> str:
        """Unique validator name."""
        return "step_marker"

    def validate(self, response: str, context: dict) -> list[ValidationIssue]:
        """
        Validate that response contains a valid STEP marker.

        Args:
            response: The LLM response text
            context: Validation context (unused)

        Returns:
            List of validation issues (empty if valid)
        """
        # Find ALL step markers and validate the LAST one
        # (responses may contain examples with <!-- STEP: X --> in docs)
        matches = re.findall(self.PATTERN, response)

        if not matches:
            return [
                ValidationIssue(
                    code="MISSING_STEP_MARKER",
                    message="Response enthält keinen STEP-Marker",
                    fix_hint="Füge am Ende hinzu: <!-- STEP: what|why|constraints|generate|finalize|done -->",
                )
            ]

        # Use the LAST step marker (the actual one, not examples)
        step = matches[-1].lower()
        if step not in self.VALID_STEPS:
            return [
                ValidationIssue(
                    code="INVALID_STEP",
                    message=f"Ungültiger Step: {step}",
                    fix_hint=f"Gültige Steps: {', '.join(sorted(self.VALID_STEPS))}",
                )
            ]

        return []

    def apply_fallback(self, response: str, context: dict) -> Optional[str]:
        """
        Apply fallback heuristics to add missing STEP marker.

        Uses content analysis to determine the likely step:
        - ADR with "erstellt" or YAML -> generate
        - ADR with "finalisiert" -> finalize
        - Questions at the end -> what (still gathering info)
        - Constraints/Rahmenbedingungen -> constraints
        - Default -> done

        Args:
            response: The response without STEP marker
            context: Validation context (unused)

        Returns:
            Response with added STEP marker
        """
        # Check if already has a valid marker (shouldn't reach here, but be safe)
        if re.search(self.PATTERN, response):
            return response

        # Determine step based on content
        step = self._infer_step(response)

        # Add marker at the end
        return f"{response.rstrip()}\n\n<!-- STEP: {step} -->"

    def _infer_step(self, response: str) -> str:
        """
        Infer the conversation step from response content.

        Args:
            response: The response text to analyze

        Returns:
            Inferred step name
        """
        response_lower = response.lower()

        # Check for ADR generation indicators
        has_adr = "adr-" in response_lower or "---\nadr_id:" in response
        has_yaml_block = "```yaml" in response_lower

        if has_adr and ("erstellt" in response_lower or has_yaml_block):
            return "generate"

        if has_adr and "finalisiert" in response_lower:
            return "finalize"

        # Check for questions (likely still gathering info)
        # Look at last portion of response for questions
        last_portion = response[-500:] if len(response) > 500 else response
        if "?" in last_portion:
            # Count questions - if multiple, likely still in discussion
            question_count = last_portion.count("?")
            if question_count >= 1:
                return "what"

        # Check for constraints discussion
        constraint_keywords = [
            "constraints",
            "rahmenbedingungen",
            "einschränkungen",
            "limitierungen",
            "anforderungen",
        ]
        if any(kw in response_lower for kw in constraint_keywords):
            return "constraints"

        # Check for why/motivation discussion
        why_keywords = ["warum", "motivation", "grund", "hintergrund", "because"]
        if any(kw in response_lower for kw in why_keywords):
            return "why"

        # Default to unknown - be honest when we can't determine the step
        # DO NOT use "done" here - that's sugar coating incomplete responses!
        return "unknown"


def extract_step(response: str) -> Optional[str]:
    """
    Extract the step name from a response.

    Utility function for parsing STEP markers.

    Args:
        response: Response text to parse

    Returns:
        Step name if found, None otherwise
    """
    match = re.search(StepMarkerValidator.PATTERN, response)
    if match:
        return match.group(1).lower()
    return None
