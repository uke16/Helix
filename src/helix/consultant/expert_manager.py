"""
Domain Expert Management for HELIX v4 Consultant System.

This module manages domain expert configurations, including loading expert
definitions, keyword-based expert selection, and expert directory setup.

ADR-034 Note:
Expert selection via keywords is now advisory, not mandatory.
The LLM (Meta-Consultant) has access to all domain expertise and decides
which domain knowledge to apply based on the conversation context.
The keyword-based selection serves as hints/suggestions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from helix.config.paths import PathConfig


@dataclass
class ExpertConfig:
    """Configuration for a domain expert.

    Attributes:
        id: Unique identifier for the expert.
        name: Human-readable name of the expert.
        description: Description of the expert's domain and capabilities.
        skills: List of skills this expert possesses.
        triggers: Keywords that suggest this expert's involvement (advisory).
    """

    id: str
    name: str
    description: str
    skills: list[str] = field(default_factory=list)
    triggers: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, expert_id: str, data: dict[str, Any]) -> ExpertConfig:
        """Create an ExpertConfig from a dictionary.

        Args:
            expert_id: The unique identifier for this expert.
            data: Dictionary containing expert configuration.

        Returns:
            ExpertConfig instance.
        """
        return cls(
            id=expert_id,
            name=data.get("name", expert_id.title()),
            description=data.get("description", ""),
            skills=data.get("skills", []),
            triggers=data.get("triggers", [])
        )


class ExpertManager:
    """
    Manages domain expert configurations for HELIX v4.

    The ExpertManager is responsible for:
    - Loading expert definitions from YAML configuration
    - Suggesting appropriate experts based on request keywords (advisory)
    - Setting up expert directories with CLAUDE.md files

    ADR-034: Expert selection is now advisory. The LLM decides which
    domain knowledge is relevant based on conversation context. The
    keyword-based selection provides hints, not mandatory assignments.

    Args:
        config_path: Path to the domain-experts.yaml configuration file.
    """

    DEFAULT_CONFIG_PATH = PathConfig.DOMAIN_EXPERTS_CONFIG

    # Default expert configurations (Company-specific)
    DEFAULT_EXPERTS: dict[str, dict[str, Any]] = {
        "helix": {
            "name": "HELIX Architecture Expert",
            "description": "Expert for HELIX v4 architecture, ADRs, and system design",
            "skills": [
                "system-architecture",
                "adr-analysis",
                "integration-patterns",
                "workflow-design"
            ],
            "triggers": [
                "helix", "architektur", "architecture", "adr",
                "workflow", "system", "integration", "orchestrierung"
            ]
        },
        "pdm": {
            "name": "Product Data Management Expert",
            "description": "Expert for product data, BOMs, revisions, and PLM systems",
            "skills": [
                "bom-management",
                "revision-control",
                "product-lifecycle",
                "data-modeling"
            ],
            "triggers": [
                "pdm", "stückliste", "bom", "revision", "produkt",
                "artikel", "material", "plm", "teile", "komponenten"
            ]
        },
        "encoder": {
            "name": "Encoder Technology Expert",
            "description": "Expert for rotary encoders, POSITAL products, and encoder specifications",
            "skills": [
                "encoder-technology",
                "posital-products",
                "sensor-specifications",
                "industrial-automation"
            ],
            "triggers": [
                "encoder", "drehgeber", "posital", "sensor",
                "absolut", "inkremental", "resolver", "winkelmessung"
            ]
        },
        "erp": {
            "name": "ERP Integration Expert",
            "description": "Expert for SAP integration, order management, and ERP processes",
            "skills": [
                "sap-integration",
                "order-management",
                "erp-processes",
                "business-logic"
            ],
            "triggers": [
                "erp", "sap", "auftrag", "order", "bestellung",
                "rechnung", "lieferung", "material", "stammdaten"
            ]
        },
        "infrastructure": {
            "name": "Infrastructure Expert",
            "description": "Expert for Docker, Proxmox, CI/CD, and cloud infrastructure",
            "skills": [
                "docker",
                "kubernetes",
                "ci-cd",
                "proxmox",
                "infrastructure-as-code"
            ],
            "triggers": [
                "docker", "container", "kubernetes", "k8s",
                "ci/cd", "pipeline", "proxmox", "deployment",
                "infrastructure", "server", "cloud"
            ]
        },
        "database": {
            "name": "Database Expert",
            "description": "Expert for PostgreSQL, Neo4j, Qdrant, and data persistence",
            "skills": [
                "postgresql",
                "neo4j",
                "qdrant",
                "data-modeling",
                "query-optimization"
            ],
            "triggers": [
                "database", "datenbank", "postgresql", "postgres",
                "neo4j", "graph", "qdrant", "vector", "sql",
                "query", "schema", "migration"
            ]
        },
        "webshop": {
            "name": "Webshop Expert",
            "description": "Expert for Company Webshop, product configurator, and e-commerce",
            "skills": [
                "e-commerce",
                "product-configuration",
                "web-frontend",
                "order-processing"
            ],
            "triggers": [
                "webshop", "shop", "konfigurator", "configurator",
                "e-commerce", "online", "bestellung", "warenkorb",
                "checkout", "produkt-auswahl"
            ]
        }
    }

    def __init__(self, config_path: Path | None = None) -> None:
        """Initialize the ExpertManager.

        Args:
            config_path: Optional path to the configuration file.
                        Defaults to PathConfig.DOMAIN_EXPERTS_CONFIG.
        """
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self._experts_cache: dict[str, ExpertConfig] | None = None

    def load_experts(self) -> dict[str, ExpertConfig]:
        """Load expert configurations from YAML file or defaults.

        Attempts to load from the configured YAML file. If the file
        doesn't exist, falls back to built-in default configurations.

        Returns:
            Dictionary mapping expert IDs to ExpertConfig instances.
        """
        if self._experts_cache is not None:
            return self._experts_cache

        experts: dict[str, ExpertConfig] = {}

        # Try loading from YAML file
        if self.config_path.exists():
            try:
                content = self.config_path.read_text(encoding="utf-8")
                data = yaml.safe_load(content)

                if isinstance(data, dict):
                    experts_data = data.get("experts", data)
                    for expert_id, expert_data in experts_data.items():
                        if isinstance(expert_data, dict):
                            experts[expert_id] = ExpertConfig.from_dict(
                                expert_id, expert_data
                            )
            except (yaml.YAMLError, IOError) as e:
                # Log error and fall back to defaults
                print(f"Warning: Could not load experts config: {e}")

        # Fall back to defaults if no experts loaded
        if not experts:
            for expert_id, expert_data in self.DEFAULT_EXPERTS.items():
                experts[expert_id] = ExpertConfig.from_dict(expert_id, expert_data)

        self._experts_cache = experts
        return experts

    def suggest_experts(self, request: str) -> list[str]:
        """Suggest experts based on keywords in the request.

        ADR-034: This method provides advisory suggestions only.
        The LLM (Meta-Consultant) decides which domain knowledge
        to apply based on full conversation context.

        Analyzes the request text and suggests experts whose trigger
        keywords are found in the request.

        Args:
            request: The user request to analyze.

        Returns:
            List of expert IDs that might be relevant (advisory).
        """
        experts = self.load_experts()
        request_lower = request.lower()

        # Normalize request for better matching
        request_normalized = re.sub(r'[^\w\s]', ' ', request_lower)
        words = set(request_normalized.split())

        scores: dict[str, int] = {}

        for expert_id, expert in experts.items():
            score = 0
            for trigger in expert.triggers:
                trigger_lower = trigger.lower()

                # Check for exact word match
                if trigger_lower in words:
                    score += 2

                # Check for partial match (substring)
                elif trigger_lower in request_lower:
                    score += 1

            if score > 0:
                scores[expert_id] = score

        # Sort by score and return as suggestions
        sorted_experts = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

        # If no experts matched, suggest 'helix' as default
        if not sorted_experts:
            sorted_experts = ["helix"]

        return sorted_experts

    # Keep select_experts as alias for backwards compatibility
    def select_experts(self, request: str) -> list[str]:
        """Select experts based on keywords in the request.

        DEPRECATED: Use suggest_experts() instead. This method now
        returns advisory suggestions, not mandatory selections.
        See ADR-034 for details.

        Args:
            request: The user request to analyze.

        Returns:
            List of expert IDs that might be relevant (advisory).
        """
        return self.suggest_experts(request)

    async def setup_expert_directory(
        self,
        expert_id: str,
        phase_dir: Path,
        question: str
    ) -> Path:
        """Set up a directory for an expert's analysis work.

        Creates the expert directory structure and generates a
        CLAUDE.md file tailored to the expert's domain.

        Args:
            expert_id: The ID of the expert.
            phase_dir: The phase directory for expert work.
            question: The specific question for this expert.

        Returns:
            Path to the created expert directory.
        """
        experts = self.load_experts()
        expert = experts.get(expert_id)

        if not expert:
            raise ValueError(f"Unknown expert: {expert_id}")

        # Create expert directory
        expert_dir = phase_dir / f"{expert_id}-expert"
        expert_dir.mkdir(parents=True, exist_ok=True)

        # Create output directory
        (expert_dir / "output").mkdir(exist_ok=True)

        # Generate and write CLAUDE.md
        claude_md = self.generate_expert_claude_md(expert, question)
        (expert_dir / "CLAUDE.md").write_text(claude_md, encoding="utf-8")

        return expert_dir

    def generate_expert_claude_md(self, expert: ExpertConfig, question: str) -> str:
        """Generate a CLAUDE.md file for an expert's analysis session.

        Creates a markdown file that instructs Claude on how to act
        as the specified domain expert.

        Args:
            expert: The expert configuration.
            question: The specific question to analyze.

        Returns:
            CLAUDE.md content as a string.
        """
        skills_list = "\n".join([f"- {skill}" for skill in expert.skills])

        return f"""# {expert.name}

Du bist ein **{expert.name}** im HELIX v4 Consultant Meeting.

## Deine Expertise

{expert.description}

## Deine Skills

{skills_list}

## Deine Aufgabe

Analysiere die folgende Frage aus deiner Fachperspektive:

> {question}

## Output-Format

Erstelle eine `output/analysis.json` mit folgendem Format:

```json
{{
    "domain": "{expert.id}",
    "findings": [
        "Beobachtung 1 aus deiner Fachperspektive",
        "Beobachtung 2 ..."
    ],
    "requirements": [
        "Technische Anforderung 1",
        "Technische Anforderung 2"
    ],
    "constraints": [
        "Einschränkung oder Randbedingung 1",
        "Einschränkung 2"
    ],
    "recommendations": [
        "Empfehlung 1",
        "Empfehlung 2"
    ],
    "dependencies": [
        "Abhängigkeit zu System X",
        "Abhängigkeit zu Komponente Y"
    ],
    "open_questions": [
        "Offene Frage, die geklärt werden muss"
    ]
}}
```

## Wichtige Regeln

1. **Fokus**: Bleibe bei deiner Fachdomäne ({expert.id})
2. **Konkret**: Gib spezifische, umsetzbare Empfehlungen
3. **Ehrlich**: Benenne Unsicherheiten und offene Fragen
4. **Kooperativ**: Berücksichtige Schnittstellen zu anderen Domains
"""

    def clear_cache(self) -> None:
        """Clear the experts cache to force reload on next access."""
        self._experts_cache = None

    def get_expert(self, expert_id: str) -> ExpertConfig | None:
        """Get a single expert configuration by ID.

        Args:
            expert_id: The expert ID to look up.

        Returns:
            ExpertConfig if found, None otherwise.
        """
        experts = self.load_experts()
        return experts.get(expert_id)

    def list_expert_ids(self) -> list[str]:
        """Get a list of all available expert IDs.

        Returns:
            List of expert IDs.
        """
        return list(self.load_experts().keys())

    def get_all_triggers(self) -> dict[str, list[str]]:
        """Get all trigger keywords for all experts.

        Returns:
            Dictionary mapping expert IDs to their trigger lists.
        """
        experts = self.load_experts()
        return {
            expert_id: expert.triggers
            for expert_id, expert in experts.items()
        }
