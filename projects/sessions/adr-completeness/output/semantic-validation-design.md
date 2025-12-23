# Layer 4: Semantic Validation - Implementation Design

> **Empfehlung für die LLM-basierte ADR-Vollständigkeitsprüfung**

---

## 1. Kontext

Layer 4 (Semantic/LLM) wurde in `adr-completeness.md` definiert als:
- Aktiviert nur für `change_scope: major` + `status: Proposed`
- Prüft semantische Vollständigkeit (nicht nur Struktur)
- Gibt Verbesserungsvorschläge

Die Frage: **Wie wird das technisch implementiert?**

---

## 2. Optionen-Analyse

### Option A: Claude Code CLI Instanz

```bash
subprocess.run(["claude", "-p", f"Prüfe: {adr_content}", "--output-format", "json"])
```

| Kriterium | Bewertung | Begründung |
|-----------|-----------|------------|
| HELIX-Architektur | ⚠️ Passt | Nutzt bestehende Infrastruktur |
| Standalone | ✅ Ja | Funktioniert überall wo Claude CLI installiert |
| Performance | ❌ Langsam | 10-30 Sekunden pro Call |
| Kosten | ⚠️ Hoch | Volle Claude-Instanz mit Tools |
| Implementierung | ⚠️ Mittel | Subprocess-Handling, Output-Parsing |

**Problem:** Claude CLI startet eine vollständige Instanz mit Tools, System Prompt etc. - Overkill für eine einfache Validierung.

### Option B: Direkter API-Call

```python
import anthropic
client = anthropic.Client()
response = client.messages.create(model="claude-sonnet-4-20250514", messages=[...])
```

| Kriterium | Bewertung | Begründung |
|-----------|-----------|------------|
| HELIX-Architektur | ⚠️ Neue Dependency | anthropic SDK nicht in requirements |
| Standalone | ⚠️ Bedingt | Benötigt API-Key |
| Performance | ✅ Schnell | 2-5 Sekunden |
| Kosten | ✅ Niedrig | Nur Sonnet, kein Tool-Overhead |
| Implementierung | ✅ Einfach | 20 Zeilen Code |

**Problem:** API-Key Management. Wo kommt der Key her wenn standalone?

### Option C: Als Quality Gate

```yaml
quality_gate:
  type: adr_complete
  semantic_review: true
```

| Kriterium | Bewertung | Begründung |
|-----------|-----------|------------|
| HELIX-Architektur | ✅ Perfekt | Passt in QualityGateRunner |
| Standalone | ❌ Nein | Nur in HELIX-Kontext |
| Performance | ⚠️ Variabel | Abhängig von Implementation |
| Kosten | ✅ Kontrolliert | Gate entscheidet ob LLM nötig |
| Implementierung | ⚠️ Mittel | Neues Gate + LLM-Integration |

**Problem:** Nicht standalone nutzbar. `adr_tool validate` würde ohne HELIX nicht semantisch prüfen.

### Option D: Hybrid - Tool + Optional LLM

```python
def validate_adr(path, semantic=False):
    result = structural_check(path)    # Layer 1-3
    if semantic:
        result += semantic_check(path)  # Layer 4
    return result
```

| Kriterium | Bewertung | Begründung |
|-----------|-----------|------------|
| HELIX-Architektur | ✅ Ja | Integrierbar in Gate |
| Standalone | ✅ Ja | `--semantic` Flag aktiviert |
| Performance | ✅ Schnell | LLM nur wenn angefordert |
| Kosten | ✅ Kontrolliert | User entscheidet |
| Implementierung | ⚠️ Mittel | Muss beide Wege unterstützen |

---

## 3. Empfehlung: Option D + E (Erweiterter Hybrid)

### Kernidee: LLMClient wiederverwenden

HELIX hat bereits einen `LLMClient` in `src/helix/llm_client.py`:

```python
class LLMClient:
    async def complete(self, model_spec: str, messages: list) -> str:
        """Einheitliche API für alle Provider."""
```

**Lösung:** Den bestehenden LLMClient nutzen, aber mit Fallback auf direkten API-Call für Standalone.

### Architektur

```
┌─────────────────────────────────────────────────────────────────────────┐
│  SEMANTIC VALIDATION ARCHITECTURE                                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  src/helix/adr/                                                          │
│  ├── validator.py        (bestehend)                                    │
│  ├── completeness.py     (Layer 2-3, aus adr-completeness.md)           │
│  └── semantic.py         (NEU - Layer 4)                                │
│       └── SemanticValidator                                             │
│           ├── check(adr, llm_client=None)                               │
│           └── _call_llm(prompt)                                         │
│               ├── Wenn llm_client: nutze HELIX LLMClient               │
│               └── Sonst: fallback auf anthropic SDK                     │
│                                                                          │
│  src/helix/tools/adr_tool.py                                            │
│  └── validate_adr(..., semantic=False)                                  │
│      └── Wenn semantic:                                                 │
│          └── SemanticValidator().check(adr)                             │
│                                                                          │
│  src/helix/quality_gates/                                               │
│  └── adr_complete.py                                                    │
│      └── ADRCompleteGate                                                │
│          └── check()                                                    │
│              └── Wenn major + proposed:                                 │
│                  └── SemanticValidator().check(adr, llm_client)        │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Implementation

```python
# src/helix/adr/semantic.py

"""Semantic validation for ADRs using LLM.

Layer 4 of the ADR Completeness system.
Uses LLM to check semantic completeness, not just structural.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .parser import ADRDocument
from .validator import ValidationIssue, IssueLevel, IssueCategory


@dataclass
class SemanticResult:
    """Result of semantic validation."""
    passed: bool
    issues: list[ValidationIssue]
    suggestions: list[str]
    llm_response: str  # Raw response for debugging


SEMANTIC_PROMPT = """Du bist ein ADR-Reviewer. Prüfe dieses ADR auf semantische Vollständigkeit.

## ADR Content
```markdown
{adr_content}
```

## ADR Metadata
- change_scope: {change_scope}
- classification: {classification}
- component_type: {component_type}

## Prüfkriterien

1. **Kontext**: Ist das "Warum" klar erklärt? Fehlt wichtiger Kontext?
2. **Entscheidung**: Ist die Entscheidung eindeutig? Gibt es Alternativen die erwähnt werden sollten?
3. **Implementation**: Ist die Implementation konkret genug für einen Entwickler?
4. **Migration** (wenn major): Gibt es einen konkreten Migrationsplan mit Schritten?
5. **Akzeptanzkriterien**: Sind die Kriterien testbar und vollständig?
6. **Konsequenzen**: Werden Trade-offs ehrlich beschrieben?

## Output Format

Antworte im folgenden JSON-Format:
```json
{{
  "passed": true/false,
  "issues": [
    {{"level": "error|warning", "message": "Beschreibung"}}
  ],
  "suggestions": [
    "Verbesserungsvorschlag 1",
    "Verbesserungsvorschlag 2"
  ]
}}
```

Nur "error" level wenn etwas kritisch fehlt. "warning" für Verbesserungsvorschläge.
"""


class SemanticValidator:
    """Validates ADRs semantically using LLM.

    Example:
        >>> validator = SemanticValidator()
        >>> result = validator.check(adr_document)
        >>> if not result.passed:
        ...     for issue in result.issues:
        ...         print(issue.message)
    """

    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        """Initialize semantic validator.

        Args:
            model: Model to use for validation. Default: claude-sonnet-4-20250514
        """
        self.model = model

    def check(
        self,
        adr: ADRDocument,
        llm_client=None,
    ) -> SemanticResult:
        """Check ADR for semantic completeness.

        Args:
            adr: Parsed ADR document
            llm_client: Optional HELIX LLMClient instance

        Returns:
            SemanticResult with issues and suggestions
        """
        prompt = SEMANTIC_PROMPT.format(
            adr_content=adr.raw_content,
            change_scope=adr.metadata.change_scope.value if adr.metadata.change_scope else "N/A",
            classification=adr.metadata.classification.value if adr.metadata.classification else "N/A",
            component_type=adr.metadata.component_type.value if adr.metadata.component_type else "N/A",
        )

        response = self._call_llm(prompt, llm_client)
        return self._parse_response(response)

    def _call_llm(self, prompt: str, llm_client=None) -> str:
        """Call LLM for semantic check.

        Uses HELIX LLMClient if provided, otherwise falls back to anthropic SDK.
        """
        if llm_client:
            # HELIX context - use existing client
            import asyncio
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(
                llm_client.complete(
                    model_spec=self.model,
                    messages=[{"role": "user", "content": prompt}]
                )
            )

        # Standalone - use anthropic SDK directly
        return self._call_anthropic_direct(prompt)

    def _call_anthropic_direct(self, prompt: str) -> str:
        """Direct API call without HELIX infrastructure."""
        try:
            import anthropic
        except ImportError:
            raise ImportError(
                "anthropic package required for standalone semantic validation. "
                "Install with: pip install anthropic"
            )

        # API key from environment
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable required for semantic validation"
            )

        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )

        return response.content[0].text

    def _parse_response(self, response: str) -> SemanticResult:
        """Parse LLM response to SemanticResult."""
        import json
        import re

        # Extract JSON from response
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to parse whole response as JSON
            json_str = response

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            # Fallback: assume passed with warning
            return SemanticResult(
                passed=True,
                issues=[ValidationIssue(
                    level=IssueLevel.WARNING,
                    category=IssueCategory.SEMANTIC,
                    message="LLM response could not be parsed",
                    location="semantic_check",
                )],
                suggestions=[],
                llm_response=response,
            )

        issues = []
        for issue_data in data.get("issues", []):
            level = IssueLevel.ERROR if issue_data.get("level") == "error" else IssueLevel.WARNING
            issues.append(ValidationIssue(
                level=level,
                category=IssueCategory.SEMANTIC,
                message=issue_data.get("message", "Unknown issue"),
                location="semantic_check",
            ))

        return SemanticResult(
            passed=data.get("passed", True),
            issues=issues,
            suggestions=data.get("suggestions", []),
            llm_response=response,
        )


def should_semantic_validate(adr: ADRDocument) -> bool:
    """Check if ADR should undergo semantic validation.

    Returns True for:
    - change_scope: major
    - status: Proposed
    """
    from .parser import ChangeScope, ADRStatus

    is_major = adr.metadata.change_scope == ChangeScope.MAJOR
    is_proposed = adr.metadata.status == ADRStatus.PROPOSED

    return is_major and is_proposed
```

### CLI Integration

```python
# src/helix/tools/adr_tool.py - Erweiterungen

def validate_adr(
    adr_path: str | Path,
    concept_path: str | Path = None,
    semantic: bool = False,
    strict: bool = False,
) -> ADRToolResult:
    """Validate an ADR file.

    Args:
        adr_path: Path to the ADR file
        concept_path: Optional path to source concept document
        semantic: Run semantic (LLM) validation
        strict: If True, treat warnings as errors
    """
    # ... existing validation ...

    # Layer 4: Semantic Validation (optional)
    if semantic:
        try:
            from helix.adr.semantic import SemanticValidator, should_semantic_validate

            if should_semantic_validate(adr):
                semantic_validator = SemanticValidator()
                semantic_result = semantic_validator.check(adr)

                for issue in semantic_result.issues:
                    if issue.level == IssueLevel.ERROR:
                        errors.append(f"[Semantic] {issue.message}")
                    else:
                        warnings.append(f"[Semantic] {issue.message}")

                if semantic_result.suggestions:
                    for suggestion in semantic_result.suggestions:
                        warnings.append(f"[Suggestion] {suggestion}")
            else:
                warnings.append(
                    "Semantic validation skipped: "
                    "Only for change_scope=major + status=Proposed"
                )
        except Exception as e:
            warnings.append(f"Semantic validation failed: {e}")

    # ... rest of function ...
```

### CLI Befehle

```bash
# Standard-Validierung (Layer 1-3, deterministisch)
python -m helix.tools.adr_tool validate ADR-014.md

# Mit semantischer Prüfung (Layer 4, LLM)
python -m helix.tools.adr_tool validate ADR-014.md --semantic

# Vollständige Prüfung mit Konzept-Diff
python -m helix.tools.adr_tool validate ADR-014.md --semantic --concept output/concept.md

# Strict mode (Warnings = Errors)
python -m helix.tools.adr_tool validate ADR-014.md --semantic --strict
```

---

## 4. Quality Gate Integration

```python
# src/helix/adr/gate.py - Erweiterungen

class ADRCompleteGate:
    """Extended ADR gate with semantic validation."""

    def check(self, config: dict, llm_client=None) -> GateResult:
        """Check ADR completeness.

        Automatically enables semantic validation for:
        - change_scope: major
        - status: Proposed
        """
        adr_path = self._resolve_path(config["file"])
        concept_path = config.get("concept")

        # Parse ADR
        parser = ADRParser()
        adr = parser.parse_file(adr_path)

        errors = []
        warnings = []

        # Layer 1: Structural (existing)
        structural_result = self._structural_check(adr)
        errors.extend(structural_result.errors)
        warnings.extend(structural_result.warnings)

        # Layer 2-3: Contextual Rules
        completeness = CompletenessValidator()
        completeness_result = completeness.check(adr)
        for issue in completeness_result.issues:
            if issue.level == IssueLevel.ERROR:
                errors.append(issue.message)
            else:
                warnings.append(issue.message)

        # Layer 4: Semantic (automatic for major + proposed)
        if should_semantic_validate(adr):
            try:
                semantic = SemanticValidator()
                semantic_result = semantic.check(adr, llm_client)

                for issue in semantic_result.issues:
                    # Semantic issues are always warnings in gate context
                    warnings.append(f"[Semantic] {issue.message}")

                for suggestion in semantic_result.suggestions:
                    warnings.append(f"[Suggestion] {suggestion}")

            except Exception as e:
                warnings.append(f"Semantic validation failed: {e}")

        return GateResult(
            passed=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )
```

### phases.yaml Usage

```yaml
# Automatisch semantic für major + proposed
phases:
  - id: consultant
    quality_gate:
      type: adr_complete
      file: output/ADR-*.md
      concept: output/concept.md

# Explizit deaktivieren
phases:
  - id: consultant
    quality_gate:
      type: adr_complete
      file: output/ADR-*.md
      semantic: false  # Disable even for major
```

---

## 5. Kosten-Bewusstsein

### Kostenabschätzung

| Szenario | Tokens (Input) | Tokens (Output) | Kosten (Sonnet) |
|----------|----------------|-----------------|-----------------|
| Kleines ADR (~500 Zeilen) | ~2000 | ~500 | ~$0.01 |
| Großes ADR (~2000 Zeilen) | ~8000 | ~800 | ~$0.04 |
| 10 ADRs pro Tag | ~50000 | ~5000 | ~$0.25/Tag |

### Kostenoptimierungen

1. **Nur bei major + proposed**: Automatische Einschränkung
2. **Caching**: Identische ADRs nicht erneut prüfen
3. **Model-Wahl**: Sonnet statt Opus (10x günstiger)
4. **Truncation**: Sehr lange ADRs kürzen

```python
# Optional: Caching
class SemanticValidator:
    def __init__(self):
        self._cache = {}  # {content_hash: result}

    def check(self, adr, llm_client=None):
        content_hash = hashlib.md5(adr.raw_content.encode()).hexdigest()
        if content_hash in self._cache:
            return self._cache[content_hash]

        result = self._do_check(adr, llm_client)
        self._cache[content_hash] = result
        return result
```

---

## 6. Dependencies

### Neue Dependencies

```toml
# pyproject.toml
[project.optional-dependencies]
semantic = [
    "anthropic>=0.40.0",  # Für standalone semantic validation
]
```

### Installation

```bash
# Ohne semantic (default)
pip install helix

# Mit semantic
pip install helix[semantic]

# Oder manuell
pip install anthropic
```

---

## 7. Zusammenfassung

### Empfohlene Lösung: Option D+ (Erweiterter Hybrid)

| Aspekt | Umsetzung |
|--------|-----------|
| **Architektur** | `src/helix/adr/semantic.py` als neues Modul |
| **HELIX-Integration** | Nutzt bestehenden `LLMClient` wenn verfügbar |
| **Standalone** | Fallback auf `anthropic` SDK mit Env-Variable |
| **Aktivierung** | `--semantic` Flag oder automatisch bei major+proposed |
| **Kosten** | Nur Sonnet, nur wenn nötig, optional caching |
| **Quality Gate** | `adr_complete` Gate mit automatischer Semantic |

### Implementierungsaufwand

| Task | Aufwand |
|------|---------|
| `semantic.py` implementieren | ~100 Zeilen |
| `adr_tool.py` erweitern | ~30 Zeilen |
| `gate.py` erweitern | ~50 Zeilen |
| Tests | ~150 Zeilen |
| **Gesamt** | ~330 Zeilen |

### Entscheidungsmatrix

```
                    ┌───────────────────────────────────────────────────┐
                    │              EMPFOHLENE LÖSUNG                     │
                    ├───────────────────────────────────────────────────┤
                    │                                                    │
                    │  ✅ Passt in HELIX-Architektur                    │
                    │  ✅ Standalone nutzbar (mit anthropic SDK)        │
                    │  ✅ Performance akzeptabel (2-5 Sekunden)         │
                    │  ✅ Kosten-bewusst (nur Sonnet, nur wenn nötig)   │
                    │  ✅ Einfach zu implementieren (~330 Zeilen)       │
                    │                                                    │
                    └───────────────────────────────────────────────────┘
```

---

*Empfehlung erstellt vom HELIX Meta-Consultant*
*Session: adr-completeness*
