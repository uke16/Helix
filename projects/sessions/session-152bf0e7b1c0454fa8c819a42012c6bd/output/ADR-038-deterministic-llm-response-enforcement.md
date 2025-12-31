---
adr_id: "038"
title: "Deterministic LLM Response Enforcement"
status: Proposed

component_type: SERVICE
classification: NEW
change_scope: major

domain: helix
language: python
skills:
  - helix
  - infrastructure

files:
  create:
    - src/helix/enforcement/__init__.py
    - src/helix/enforcement/response_enforcer.py
    - src/helix/enforcement/validators/__init__.py
    - src/helix/enforcement/validators/step_marker.py
    - src/helix/enforcement/validators/adr_structure.py
    - src/helix/enforcement/validators/file_existence.py
    - src/helix/enforcement/validators/base.py
    - tests/unit/enforcement/test_response_enforcer.py
    - tests/unit/enforcement/test_validators.py
  modify:
    - src/helix/consultant/claude_runner.py
    - src/helix/api/routes/openai.py
    - src/helix/consultant/session_manager.py
  docs:
    - docs/ARCHITECTURE-MODULES.md

depends_on:
  - ADR-025
  - ADR-034
---

# ADR-038: Deterministic LLM Response Enforcement

## Status

Proposed

## Kontext

### Das Problem

Der HELIX Consultant basiert auf LLM-generierten Antworten. Das LLM **soll** bestimmte Strukturen und Marker einhalten:

1. **STEP-Marker**: `<!-- STEP: what|why|constraints|generate|finalize|done -->` am Ende jeder Antwort
2. **ADR-Struktur**: Pflicht-Sections (Kontext, Entscheidung, Akzeptanzkriterien) wenn ein ADR erstellt wird
3. **Datei-Referenzen**: `files.modify` im YAML-Header darf nur existierende Dateien referenzieren
4. **Status-Updates**: Session-Status muss aktualisiert werden

**Aktueller Zustand:**
- LLM kann diese Anforderungen vergessen
- Kein Enforcement-Mechanismus existiert
- Step-Tracking ist unvollständig wenn Marker fehlt
- ADRs können unvollständig sein

**Konsequenzen ohne Fix:**
- Observability-Daten unvollständig (Step-History)
- Manuelle Nacharbeit bei unvollständigen ADRs
- Pipeline-Fehler wenn referenzierte Dateien nicht existieren
- Inkonsistente Session-Status

### Bestehende Systeme

| Komponente | Was existiert | Limitation |
|------------|---------------|------------|
| SubAgentVerifier | 3-Retry-Loop mit Feedback | Nur für Pipeline-Phasen, nicht Consultant |
| RetryHandler | Exponential Backoff | Nicht für LLM-Output-Validierung |
| ADRValidator | Sections, Header prüfen | Nur nach Erstellung, kein Enforcement |

## Entscheidung

Wir implementieren einen **ResponseEnforcer** als Wrapper um den ClaudeRunner, der:

1. LLM-Responses gegen konfigurierbare Validators prüft
2. Bei Fehlern automatisch Retry mit Feedback-Prompt durchführt (max 2 Retries)
3. Fallback-Heuristiken anwendet wenn max_retries erreicht
4. Fehler an Open WebUI streamt wenn kein Recovery möglich

### Architektur

```
┌─────────────────────────────────────────────────────────────────┐
│                    LLM Response Flow                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ClaudeRunner                                                   │
│       │                                                          │
│       ▼                                                          │
│   ┌───────────────────┐                                          │
│   │ ResponseEnforcer  │◄─── Wrapper um ClaudeRunner              │
│   │                   │                                          │
│   │ • max_retries: 2  │                                          │
│   │ • validators: []  │                                          │
│   └─────────┬─────────┘                                          │
│             │                                                    │
│             ▼                                                    │
│   ┌───────────────────┐                                          │
│   │  Validators       │                                          │
│   │  ─────────────    │                                          │
│   │  • StepMarker     │                                          │
│   │  • ADRStructure   │                                          │
│   │  • FileExistence  │                                          │
│   └─────────┬─────────┘                                          │
│             │                                                    │
│     ┌───────┴───────┐                                            │
│     │               │                                            │
│     ▼               ▼                                            │
│  VALID           INVALID                                         │
│     │               │                                            │
│     ▼               ▼                                            │
│  Return         Retry mit Feedback                               │
│                     │                                            │
│              ┌──────┴──────┐                                     │
│              │             │                                     │
│              ▼             ▼                                     │
│         Success      Max Retries                                 │
│                           │                                      │
│                    ┌──────┴──────┐                               │
│                    │             │                               │
│                    ▼             ▼                               │
│               Fallback      Stream Error                         │
│               anwenden      an Open WebUI                        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Warum diese Lösung?

1. **Zentrale Integration**: Alle Claude-Aufrufe gehen durch einen Punkt
2. **Retry mit --continue**: Nutzt Claude's Session-Continuation (schnell, Kontext bleibt)
3. **Fallback-Mechanismus**: Wenn max_retries erreicht, wird Heuristik angewandt
4. **Erweiterbar**: Neue Validators können einfach hinzugefügt werden
5. **Observable**: Zentrale Metrics für Enforcement-Aktionen
6. **Open WebUI Integration**: Fehler werden als spezielle Events gestreamt

## Implementation

### 1. Base Validator Interface

```python
# src/helix/enforcement/validators/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class ValidationIssue:
    """Ein Validierungsproblem."""
    code: str
    message: str
    fix_hint: str
    severity: str = "error"  # error, warning


@dataclass
class ValidationResult:
    """Ergebnis einer Validierung."""
    valid: bool
    issues: list[ValidationIssue]


class ResponseValidator(ABC):
    """Base class für Response-Validatoren."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Eindeutiger Name des Validators."""
        pass

    @abstractmethod
    def validate(self, response: str, context: dict) -> list[ValidationIssue]:
        """
        Validiert eine LLM-Response.

        Args:
            response: Die LLM-Response als String
            context: Zusätzlicher Kontext (session_state, etc.)

        Returns:
            Liste von ValidationIssues (leer wenn valid)
        """
        pass

    def apply_fallback(self, response: str, context: dict) -> Optional[str]:
        """
        Wendet Fallback-Heuristik an wenn möglich.

        Returns:
            Korrigierte Response oder None wenn kein Fallback möglich
        """
        return None
```

### 2. Step Marker Validator

```python
# src/helix/enforcement/validators/step_marker.py
import re
from typing import Optional
from .base import ResponseValidator, ValidationIssue


class StepMarkerValidator(ResponseValidator):
    """Validiert dass STEP-Marker vorhanden ist."""

    PATTERN = r'<!--\s*STEP:\s*(\w+)\s*-->'
    VALID_STEPS = {"what", "why", "constraints", "generate", "finalize", "done"}

    @property
    def name(self) -> str:
        return "step_marker"

    def validate(self, response: str, context: dict) -> list[ValidationIssue]:
        """Prüft ob gültiger STEP-Marker vorhanden."""
        match = re.search(self.PATTERN, response)

        if not match:
            return [ValidationIssue(
                code="MISSING_STEP_MARKER",
                message="Response enthält keinen STEP-Marker",
                fix_hint="Füge am Ende hinzu: <!-- STEP: what|why|constraints|generate|finalize|done -->"
            )]

        step = match.group(1).lower()
        if step not in self.VALID_STEPS:
            return [ValidationIssue(
                code="INVALID_STEP",
                message=f"Ungültiger Step: {step}",
                fix_hint=f"Gültige Steps: {', '.join(sorted(self.VALID_STEPS))}"
            )]

        return []

    def apply_fallback(self, response: str, context: dict) -> Optional[str]:
        """Fallback: Heuristik-basierte Step-Zuweisung."""
        # Heuristik basierend auf Inhalt
        if "ADR-" in response and ("erstellt" in response.lower() or "```yaml" in response):
            step = "generate"
        elif "ADR-" in response and "finalisiert" in response.lower():
            step = "finalize"
        elif "?" in response[-300:]:  # Fragt etwas am Ende
            step = "discussing"
        elif any(word in response.lower() for word in ["constraints", "rahmenbedingungen"]):
            step = "constraints"
        else:
            step = "done"  # Safe default

        return f"{response}\n\n<!-- STEP: {step} -->"
```

### 3. ADR Structure Validator

```python
# src/helix/enforcement/validators/adr_structure.py
import re
import yaml
from typing import Optional
from .base import ResponseValidator, ValidationIssue


class ADRStructureValidator(ResponseValidator):
    """Validiert ADR-Struktur wenn Response ein ADR enthält."""

    REQUIRED_SECTIONS = ["Kontext", "Entscheidung", "Akzeptanzkriterien"]
    REQUIRED_YAML_FIELDS = ["adr_id", "title", "status"]

    @property
    def name(self) -> str:
        return "adr_structure"

    def validate(self, response: str, context: dict) -> list[ValidationIssue]:
        """Prüft ADR-Struktur wenn Response ein ADR ist."""
        # Nur validieren wenn es ein ADR ist
        if "---\nadr_id:" not in response and "---\n adr_id:" not in response:
            return []

        issues = []

        # YAML Header prüfen
        yaml_match = re.search(r'^---\n(.*?)\n---', response, re.DOTALL | re.MULTILINE)
        if yaml_match:
            try:
                metadata = yaml.safe_load(yaml_match.group(1))
                for field in self.REQUIRED_YAML_FIELDS:
                    if field not in metadata:
                        issues.append(ValidationIssue(
                            code="MISSING_ADR_FIELD",
                            message=f"ADR fehlt Pflichtfeld im Header: {field}",
                            fix_hint=f"Füge '{field}' zum YAML-Header hinzu"
                        ))
            except yaml.YAMLError:
                issues.append(ValidationIssue(
                    code="INVALID_YAML",
                    message="ADR hat ungültigen YAML-Header",
                    fix_hint="Prüfe YAML-Syntax im Header"
                ))
        else:
            issues.append(ValidationIssue(
                code="MISSING_YAML_HEADER",
                message="ADR fehlt YAML-Header",
                fix_hint="Füge YAML-Header mit --- Delimitern hinzu"
            ))

        # Pflicht-Sections prüfen
        for section in self.REQUIRED_SECTIONS:
            if f"## {section}" not in response:
                issues.append(ValidationIssue(
                    code="MISSING_ADR_SECTION",
                    message=f"ADR fehlt Section: ## {section}",
                    fix_hint=f"Füge Section '## {section}' mit Inhalt hinzu"
                ))

        # Akzeptanzkriterien als Checkboxen prüfen
        if "## Akzeptanzkriterien" in response:
            criteria_section = response.split("## Akzeptanzkriterien")[1]
            # Stoppe bei nächster Section
            if "## " in criteria_section[3:]:
                criteria_section = criteria_section[:criteria_section[3:].index("## ") + 3]

            checkbox_count = len(re.findall(r'- \[ \]', criteria_section))
            if checkbox_count < 3:
                issues.append(ValidationIssue(
                    code="INSUFFICIENT_CRITERIA",
                    message=f"ADR hat nur {checkbox_count} Akzeptanzkriterien (mindestens 3 empfohlen)",
                    fix_hint="Füge mehr konkrete, testbare Akzeptanzkriterien hinzu",
                    severity="warning"
                ))

        return issues

    def apply_fallback(self, response: str, context: dict) -> Optional[str]:
        """Kein Fallback für ADR-Struktur - muss manuell korrigiert werden."""
        return None
```

### 4. File Existence Validator

```python
# src/helix/enforcement/validators/file_existence.py
import re
import yaml
from pathlib import Path
from typing import Optional
from .base import ResponseValidator, ValidationIssue


class FileExistenceValidator(ResponseValidator):
    """Prüft ob referenzierte Dateien existieren."""

    def __init__(self, helix_root: Path):
        self.helix_root = helix_root

    @property
    def name(self) -> str:
        return "file_existence"

    def validate(self, response: str, context: dict) -> list[ValidationIssue]:
        """Prüft ob files.modify nur existierende Dateien referenziert."""
        # YAML Header extrahieren
        yaml_match = re.search(r'^---\n(.*?)\n---', response, re.DOTALL | re.MULTILINE)
        if not yaml_match:
            return []

        try:
            metadata = yaml.safe_load(yaml_match.group(1))
            modify_files = metadata.get("files", {}).get("modify", [])
        except (yaml.YAMLError, AttributeError):
            return []

        if not modify_files:
            return []

        issues = []
        for file_path in modify_files:
            full_path = self.helix_root / file_path
            if not full_path.exists():
                issues.append(ValidationIssue(
                    code="FILE_NOT_FOUND",
                    message=f"files.modify referenziert nicht existierende Datei: {file_path}",
                    fix_hint=f"Entferne '{file_path}' aus files.modify oder verschiebe nach files.create"
                ))

        return issues

    def apply_fallback(self, response: str, context: dict) -> Optional[str]:
        """Fallback: Nicht existierende Dateien nach files.create verschieben."""
        yaml_match = re.search(r'^---\n(.*?)\n---', response, re.DOTALL | re.MULTILINE)
        if not yaml_match:
            return None

        try:
            metadata = yaml.safe_load(yaml_match.group(1))
            modify_files = metadata.get("files", {}).get("modify", [])
            create_files = metadata.get("files", {}).get("create", [])
        except (yaml.YAMLError, AttributeError):
            return None

        # Finde nicht existierende Dateien
        moved = []
        new_modify = []
        for file_path in modify_files:
            full_path = self.helix_root / file_path
            if full_path.exists():
                new_modify.append(file_path)
            else:
                create_files.append(file_path)
                moved.append(file_path)

        if not moved:
            return None

        # YAML neu generieren (vereinfacht - in Produktion robuster)
        metadata["files"]["modify"] = new_modify
        metadata["files"]["create"] = create_files

        new_yaml = yaml.dump(metadata, allow_unicode=True, default_flow_style=False)
        return f"---\n{new_yaml}---" + response[yaml_match.end():]
```

### 5. Response Enforcer

```python
# src/helix/enforcement/response_enforcer.py
import logging
from dataclasses import dataclass
from typing import Optional, AsyncIterator

from .validators.base import ResponseValidator, ValidationIssue


logger = logging.getLogger(__name__)


@dataclass
class EnforcementResult:
    """Ergebnis der Enforcement-Prüfung."""
    success: bool
    response: str
    attempts: int
    issues: list[ValidationIssue]
    fallback_applied: bool = False


class ResponseEnforcer:
    """
    Wrapper um ClaudeRunner der LLM-Output erzwingt.

    Validiert Responses gegen konfigurierte Validators und führt
    bei Fehlern automatisch Retry mit Feedback durch.
    """

    def __init__(
        self,
        runner,  # ClaudeRunner
        max_retries: int = 2,
        validators: list[ResponseValidator] = None,
    ):
        self.runner = runner
        self.max_retries = max_retries
        self.validators = validators or []

    def add_validator(self, validator: ResponseValidator) -> None:
        """Fügt einen Validator hinzu."""
        self.validators.append(validator)

    async def run_with_enforcement(
        self,
        session_id: str,
        prompt: str,
        validator_names: list[str] = None,
        **runner_kwargs
    ) -> EnforcementResult:
        """
        Führt Claude aus und validiert Response.
        Bei Validation-Fehler: Automatic Retry mit Feedback.

        Args:
            session_id: Session ID für Continue
            prompt: Initial Prompt
            validator_names: Liste von Validator-Namen (None = alle)
            **runner_kwargs: Weitere Args für ClaudeRunner

        Returns:
            EnforcementResult mit Response und Metadata
        """
        active_validators = self._get_validators(validator_names)
        all_issues: list[ValidationIssue] = []

        for attempt in range(self.max_retries + 1):
            # Claude ausführen
            if attempt == 0:
                result = await self.runner.run_session(
                    session_id=session_id,
                    prompt=prompt,
                    **runner_kwargs
                )
            else:
                # Retry mit --continue und Feedback
                feedback_prompt = self._build_feedback_prompt(all_issues)
                result = await self.runner.continue_session(
                    session_id=session_id,
                    prompt=feedback_prompt,
                    **runner_kwargs
                )

            response = result.stdout

            # Validieren
            issues = []
            for validator in active_validators:
                issues.extend(validator.validate(response, runner_kwargs.get("context", {})))

            # Nur Errors zählen (Warnings ignorieren für Retry)
            errors = [i for i in issues if i.severity == "error"]

            if not errors:
                return EnforcementResult(
                    success=True,
                    response=response,
                    attempts=attempt + 1,
                    issues=[i for i in issues if i.severity == "warning"],
                    fallback_applied=False
                )

            all_issues = errors
            logger.warning(
                f"Response validation failed (attempt {attempt + 1}/{self.max_retries + 1}): "
                f"{[i.code for i in errors]}"
            )

        # Max retries erreicht - Fallback versuchen
        fallback_response = self._apply_fallbacks(response, all_issues, runner_kwargs.get("context", {}))

        if fallback_response:
            logger.info(f"Applied fallback for issues: {[i.code for i in all_issues]}")
            return EnforcementResult(
                success=True,
                response=fallback_response,
                attempts=self.max_retries + 1,
                issues=all_issues,
                fallback_applied=True
            )

        # Kein Fallback möglich
        return EnforcementResult(
            success=False,
            response=response,
            attempts=self.max_retries + 1,
            issues=all_issues,
            fallback_applied=False
        )

    def _get_validators(self, names: list[str] = None) -> list[ResponseValidator]:
        """Filtert Validators nach Namen."""
        if names is None:
            return self.validators
        return [v for v in self.validators if v.name in names]

    def _build_feedback_prompt(self, issues: list[ValidationIssue]) -> str:
        """Baut Feedback-Prompt für Retry."""
        lines = [
            "WICHTIG: Deine letzte Antwort hatte Validierungsfehler. Bitte korrigiere:",
            ""
        ]

        for issue in issues:
            lines.append(f"**{issue.code}**: {issue.message}")
            lines.append(f"  → Fix: {issue.fix_hint}")
            lines.append("")

        lines.append("Bitte wiederhole deine Antwort mit den Korrekturen.")

        return "\n".join(lines)

    def _apply_fallbacks(
        self,
        response: str,
        issues: list[ValidationIssue],
        context: dict
    ) -> Optional[str]:
        """Wendet Fallbacks für alle Issues an."""
        current_response = response

        for issue in issues:
            # Finde passenden Validator
            for validator in self.validators:
                validator_issues = validator.validate(current_response, context)
                if any(i.code == issue.code for i in validator_issues):
                    fallback = validator.apply_fallback(current_response, context)
                    if fallback:
                        current_response = fallback
                        break

        # Prüfen ob alle Issues gelöst
        remaining_issues = []
        for validator in self.validators:
            remaining_issues.extend(validator.validate(current_response, context))

        remaining_errors = [i for i in remaining_issues if i.severity == "error"]

        if not remaining_errors:
            return current_response

        return None

    async def stream_enforcement_error(
        self,
        issues: list[ValidationIssue]
    ) -> AsyncIterator[str]:
        """
        Streamt Enforcement-Fehler an Open WebUI.

        Format: SSE-kompatibel für Open WebUI's event stream.
        """
        yield "data: [ENFORCEMENT ERROR]\n\n"
        yield "data: Die LLM-Response konnte nicht validiert werden:\n\n"

        for issue in issues:
            yield f"data: - {issue.code}: {issue.message}\n\n"

        yield "data: Bitte versuche es erneut oder kontaktiere den Administrator.\n\n"
        yield "data: [DONE]\n\n"
```

### 6. Integration in OpenAI Route

```python
# Änderung in src/helix/api/routes/openai.py

from helix.enforcement.response_enforcer import ResponseEnforcer
from helix.enforcement.validators.step_marker import StepMarkerValidator
from helix.enforcement.validators.adr_structure import ADRStructureValidator
from helix.enforcement.validators.file_existence import FileExistenceValidator

# In der chat_completion Funktion:

async def chat_completion(request: ChatCompletionRequest, ...):
    # ... existing code ...

    # ResponseEnforcer initialisieren
    enforcer = ResponseEnforcer(
        runner=claude_runner,
        max_retries=2,
        validators=[
            StepMarkerValidator(),
            ADRStructureValidator(),
            FileExistenceValidator(helix_root=Path(HELIX_ROOT)),
        ]
    )

    # Statt direktem runner.run_session:
    result = await enforcer.run_with_enforcement(
        session_id=session_id,
        prompt=prompt,
        validator_names=["step_marker"],  # Für Chat immer Step-Marker
        context={"session_state": session_state}
    )

    if not result.success:
        # Fehler an Open WebUI streamen
        async for chunk in enforcer.stream_enforcement_error(result.issues):
            yield chunk
        return

    # Normale Response verarbeiten
    response = result.response
    # ... rest of code ...
```

### 7. Cleanup: Toter Code und Hardcoded Paths

Als Teil dieses ADRs werden auch folgende Bereinigungen durchgeführt:

#### Toter Code entfernen

```python
# session_manager.py - Diese Methoden entfernen:
# - _generate_session_id_stable() (Zeile 122-142) - nie aufgerufen
# - generate_session_id() (Zeile 146-158) - deprecated
# - _find_or_create_session_id() (Zeile 226-270) - obsolet nach ADR-035
```

#### Hardcoded Paths refactoren

```python
# config/settings.py - Zentrale Konfiguration
import os
from pathlib import Path

HELIX_ROOT = Path(os.environ.get("HELIX_ROOT", "/home/aiuser01/helix-v4"))
SESSIONS_DIR = HELIX_ROOT / "projects" / "sessions"
ADR_DIR = HELIX_ROOT / "adr"
SKILLS_DIR = HELIX_ROOT / "skills"

# In allen Dateien ersetzen:
# /home/aiuser01/helix-v4 → HELIX_ROOT
```

#### Backup-Dateien entfernen

```bash
rm src/helix/api/routes/*.bak
```

## Dokumentation

| Dokument | Änderung |
|----------|----------|
| `docs/ARCHITECTURE-MODULES.md` | Neues helix.enforcement Package dokumentieren |
| `CLAUDE.md` | Hinweis auf Step-Marker Enforcement |
| `templates/consultant/session.md.j2` | Hinweis dass Step-Marker PFLICHT ist |

## Akzeptanzkriterien

### Funktionalität

- [ ] ResponseEnforcer validiert LLM-Responses gegen Validators
- [ ] Bei Validation-Fehler wird automatisch Retry mit Feedback durchgeführt
- [ ] Nach max_retries wird Fallback-Heuristik angewandt
- [ ] StepMarkerValidator erkennt fehlende/ungültige Step-Marker
- [ ] ADRStructureValidator prüft Pflicht-Sections und YAML-Header
- [ ] FileExistenceValidator prüft files.modify gegen Dateisystem
- [ ] Fehler werden an Open WebUI als spezielle Events gestreamt

### Tests

- [ ] Unit Tests für alle Validators
- [ ] Unit Tests für ResponseEnforcer (Retry-Logic)
- [ ] Integration Tests für OpenAI Route mit Enforcement
- [ ] Test für Fallback-Anwendung

### Cleanup

- [ ] Toter Code entfernt (`_generate_session_id_stable`, etc.)
- [ ] Hardcoded Paths durch HELIX_ROOT ersetzt
- [ ] .bak Dateien gelöscht

### Dokumentation

- [ ] ARCHITECTURE-MODULES.md aktualisiert
- [ ] Docstrings für alle public APIs

## Konsequenzen

### Positiv

- **Deterministisches Verhalten**: LLM-Output wird erzwungen, nicht nur erwartet
- **Bessere Observability**: Step-Marker sind immer vorhanden
- **Weniger manuelle Nacharbeit**: ADRs sind vollständig
- **Pipeline-Stabilität**: Keine Fehler durch nicht-existierende Dateien
- **Erweiterbar**: Neue Validators können einfach hinzugefügt werden

### Negativ

- **Latenz**: Bei Retries dauert Response länger (ca. 10-30s pro Retry)
- **Kosten**: Retries verbrauchen zusätzliche Token
- **Komplexität**: Neues Package zu maintainen

### Mitigation

- Fallback-Heuristiken minimieren Retry-Bedarf
- Metrics für Retry-Rate ermöglichen Optimierung
- Klare Validator-API macht Wartung einfach

## Referenzen

- ADR-025: Sub-Agent Verifikation (ähnliches Pattern für Pipeline)
- ADR-034: Consultant Flow Refactoring (Step-Marker Definition)
- bugs/INDEX.md: Step-Marker Enforcement als Feature Request
