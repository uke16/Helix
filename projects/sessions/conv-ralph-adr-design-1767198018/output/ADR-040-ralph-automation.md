---
adr_id: "040"
title: Ralph Automation - Iterative ADR Execution Pattern
status: Proposed

project_type: helix_internal
component_type: PROCESS
classification: NEW
change_scope: major

domain: helix
language: python

skills:
  - helix
  - helix/adr

files:
  create:
    - templates/controller/CLAUDE.md.j2
    - src/helix/ralph/__init__.py
    - src/helix/ralph/controller.py
    - src/helix/ralph/promises.py
    - docs/RALPH-PATTERN.md
  modify:
    - adr/INDEX.md
    - skills/helix/adr/SKILL.md
  docs:
    - docs/RALPH-PATTERN.md
    - docs/ADR-TEMPLATE.md

depends_on:
  - ADR-025  # Sub-Agent Verifikation
  - ADR-023  # Workflow-Definitionen
---

# ADR-040: Ralph Automation - Iterative ADR Execution Pattern

## Status

📋 Proposed

---

## Kontext

### Das Problem

ADRs werden aktuell als Spezifikationen erstellt, aber die Ausführung ist nicht standardisiert:

1. **Keine einheitliche Iteration** - Jedes ADR wird anders implementiert
2. **Keine Completion Guarantees** - Unklar wann ein ADR "fertig" ist
3. **Keine Sub-Agent Validierung** - Integration Tests fehlen systematisch
4. **Keine Rolle-spezifischen Kriterien** - Developer, Reviewer etc. haben keine Standards

### Warum das Ralph Pattern?

Geoffrey Huntley's "Ralph Wiggum" Technik hat sich in ADR-039 bewährt:

- **Iterativ**: Claude arbeitet in einer Loop bis alles funktioniert
- **Selbst-korrigierend**: Fehler werden automatisch erkannt und behoben
- **Completion Promise**: Klares Signal wenn die Aufgabe erfüllt ist
- **Vorherige Arbeit sichtbar**: Git History und Status-Dateien

### Was passiert ohne Standard?

- Jedes ADR-Projekt "erfindet" seinen eigenen Workflow
- Keine Vergleichbarkeit zwischen Projekten
- Keine wiederverwendbaren Patterns
- Schwierige Integration in CI/CD

---

## Entscheidung

### Wir führen ein standardisiertes Ralph Automation System ein:

1. **Ralph Section in jedem ADR** - Standardformat für iterative Ausführung
2. **Completion Promises pro Rolle** - Definierte Abschlusskriterien
3. **Sub-Agent Freigabe Pattern** - Integration Tests als Claude-zu-Claude Aufrufe

---

## Implementation

### 1. Ralph Section Format für ADRs

Jedes ADR mit `component_type: TOOL|NODE|AGENT|SERVICE|PROCESS` MUSS eine Ralph Section haben:

```markdown
## Ralph Automation

### Completion Promise

`<promise>ADR_XXX_COMPLETE</promise>`

### Rollen und Kriterien

| Rolle | Promise | Kriterien |
|-------|---------|-----------|
| Developer | `UNIT_TESTS_PASSED` | Unit Tests grün, Syntax OK, Linter clean |
| Integrator | `INTEGRATION_TEST_PASSED` | API startet, Smoke Test OK, Sub-Agent antwortet |
| Reviewer | `CODE_REVIEW_PASSED` | ADR Requirements erfüllt, Keine Security Issues |
| Dokumentierer | `DOCS_COMPLETE` | ARCHITECTURE-MODULES.md aktualisiert, Docstrings vorhanden |

### Iteration Config

```yaml
ralph:
  max_iterations: 10
  role: developer  # oder: integrator, reviewer, dokumentierer
  completion_promise: ADR_XXX_COMPLETE
  status_file: status.md

  checks:
    - type: no_hardcoded_paths
      pattern: "/home/aiuser01"
      scope: "src/"
    - type: unit_tests
      command: "pytest tests/unit/ -v"
    - type: syntax_check
      files: ["src/**/*.py"]
```
```

### 2. Standard Completion Promises

#### Developer Promise: `UNIT_TESTS_PASSED`

```yaml
role: developer
promise: UNIT_TESTS_PASSED
criteria:
  mandatory:
    - name: "Unit Tests Green"
      check: "pytest tests/unit/ -v --tb=short"
      success: "exit_code == 0"

    - name: "Syntax Valid"
      check: "python3 -m py_compile {files}"
      success: "exit_code == 0"

    - name: "No Hardcoded Paths"
      check: "grep -r '/home/aiuser01' src/ --include='*.py'"
      success: "no_output"

  optional:
    - name: "Type Hints Complete"
      check: "pyright src/"
      success: "no_errors"
```

**Wann ausgeben:**
```python
if all_unit_tests_pass and syntax_valid and no_hardcoded_paths:
    print("<promise>UNIT_TESTS_PASSED</promise>")
```

#### Integrator Promise: `INTEGRATION_TEST_PASSED`

```yaml
role: integrator
promise: INTEGRATION_TEST_PASSED
criteria:
  mandatory:
    - name: "API Starts"
      check: "curl -s http://localhost:8001/health"
      success: "status == 200"

    - name: "Sub-Agent Response"
      check: |
        curl -s -X POST http://localhost:8001/v1/chat/completions \
          -H "Content-Type: application/json" \
          -d '{"model":"helix-consultant","messages":[{"role":"user","content":"Test"}]}'
      success: "response.choices[0].message.content.length > 50"

    - name: "No Error in Response"
      check: "response does not contain 'error' or 'Error'"
      success: "true"
```

**Sub-Agent Freigabe:**
```
Controller (Ralph Loop)
    │
    ▼
┌─────────────────────────────────┐
│  1. Implementiert Code           │
│  2. Startet API                  │
│  3. Ruft Sub-Agent auf           │
│     └── POST /v1/chat/completions│
│  4. Sub-Agent antwortet?         │
│     └── JA → Integration OK      │
│     └── NEIN → Retry Loop        │
│  5. <promise>INTEGRATION_TEST_PASSED</promise>
└─────────────────────────────────┘
```

#### Reviewer Promise: `CODE_REVIEW_PASSED`

```yaml
role: reviewer
promise: CODE_REVIEW_PASSED
criteria:
  mandatory:
    - name: "ADR Requirements Met"
      check: "Alle Akzeptanzkriterien aus ADR als [ ] oder [x] vorhanden"
      success: "no_unchecked_mandatory_criteria"

    - name: "Files Created"
      check: "Alle files.create aus ADR existieren"
      success: "all_files_exist"

    - name: "Files Modified"
      check: "Alle files.modify aus ADR wurden geändert (git diff)"
      success: "all_files_modified"

  security:
    - name: "No Secrets in Code"
      check: "grep -r 'password|secret|api_key' src/"
      success: "no_hardcoded_secrets"

    - name: "No SQL Injection"
      check: "grep -r 'f\".*SELECT.*{' src/"
      success: "no_matches"
```

#### Dokumentierer Promise: `DOCS_COMPLETE`

```yaml
role: dokumentierer
promise: DOCS_COMPLETE
criteria:
  mandatory:
    - name: "Module Documented"
      check: "files.docs aus ADR existieren und sind aktualisiert"
      success: "all_docs_updated"

    - name: "Docstrings Present"
      check: "Alle public functions/classes haben Docstrings"
      success: "pydocstyle src/{module}/"

    - name: "ARCHITECTURE-MODULES.md Updated"
      check: "Neues Modul ist in ARCHITECTURE-MODULES.md dokumentiert"
      success: "module_in_arch_docs"
```

### 3. Sub-Agent Freigabe Pattern

Das kritischste Pattern: Der Integration Test ruft einen anderen Claude auf.

```python
# src/helix/ralph/sub_agent_test.py

"""Sub-Agent Integration Test für Ralph Automation.

Testet ob ein Claude Sub-Agent (z.B. Consultant) funktioniert,
indem ein API-Call gemacht wird und die Response validiert wird.
"""

from dataclasses import dataclass
from typing import Optional
import httpx


@dataclass
class SubAgentTestResult:
    """Ergebnis eines Sub-Agent Tests."""
    passed: bool
    response_length: int
    response_preview: str
    error: Optional[str] = None


class SubAgentTester:
    """Testet Sub-Agent Funktionalität via API-Call.

    Der Test ist erfolgreich wenn:
    1. Der API-Call 200 zurückgibt
    2. Die Response > min_length Zeichen hat
    3. Die Response keine Error-Strings enthält
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8001",
        min_response_length: int = 50,
        timeout: float = 30.0,
    ):
        """Initialize SubAgentTester.

        Args:
            base_url: API base URL.
            min_response_length: Minimum chars in response to pass.
            timeout: Request timeout in seconds.
        """
        self.base_url = base_url
        self.min_response_length = min_response_length
        self.timeout = timeout

    async def test_consultant(
        self,
        prompt: str = "Antworte mit einem Satz: Was ist HELIX?",
        conversation_id: Optional[str] = None,
    ) -> SubAgentTestResult:
        """Test Consultant Sub-Agent.

        Args:
            prompt: Test prompt to send.
            conversation_id: Optional conversation ID for session persistence.

        Returns:
            SubAgentTestResult with pass/fail status.
        """
        import uuid

        headers = {
            "Content-Type": "application/json",
            "X-OpenWebUI-Chat-Id": conversation_id or f"test-{uuid.uuid4()}",
        }

        payload = {
            "model": "helix-consultant",
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    json=payload,
                    headers=headers,
                )

                if response.status_code != 200:
                    return SubAgentTestResult(
                        passed=False,
                        response_length=0,
                        response_preview="",
                        error=f"HTTP {response.status_code}: {response.text[:100]}",
                    )

                data = response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

                # Validierung
                if len(content) < self.min_response_length:
                    return SubAgentTestResult(
                        passed=False,
                        response_length=len(content),
                        response_preview=content[:100],
                        error=f"Response too short: {len(content)} < {self.min_response_length}",
                    )

                if "error" in content.lower()[:50]:
                    return SubAgentTestResult(
                        passed=False,
                        response_length=len(content),
                        response_preview=content[:100],
                        error="Response contains error message",
                    )

                return SubAgentTestResult(
                    passed=True,
                    response_length=len(content),
                    response_preview=content[:100],
                )

        except Exception as e:
            return SubAgentTestResult(
                passed=False,
                response_length=0,
                response_preview="",
                error=str(e),
            )
```

### 4. Controller Template Update

Erweitere `templates/controller/CLAUDE.md.j2`:

```jinja2
# Ralph Controller für {{ adr_id }}: {{ adr_title }}

Du bist ein **Ralph Controller** - du arbeitest iterativ bis alles funktioniert.

## WICHTIG: Ralph Loop Regeln

1. Du bekommst denselben Prompt bei jeder Iteration
2. Deine vorherige Arbeit ist in Dateien sichtbar (git history)
3. Lies `status.md` um zu sehen was du schon gemacht hast
4. Arbeite weiter wo du aufgehört hast
5. Wenn ALLES fertig ist: Output `<promise>{{ completion_promise }}</promise>`

---

## Deine Rolle: {{ role | default('developer') }}

{% if role == 'developer' %}
### Developer Kriterien

Dein Promise: `UNIT_TESTS_PASSED`

Kriterien:
- [ ] Alle Unit Tests grün: `pytest tests/unit/ -v`
- [ ] Syntax valide: `python3 -m py_compile {files}`
- [ ] Keine hardcoded Paths: `grep -r "/home/aiuser01" src/`

{% elif role == 'integrator' %}
### Integrator Kriterien

Dein Promise: `INTEGRATION_TEST_PASSED`

Kriterien:
- [ ] API startet und antwortet auf /health
- [ ] Sub-Agent Test: Consultant antwortet mit > 50 Zeichen
- [ ] Keine Errors in Response

**Sub-Agent Test Befehl:**
```bash
curl -s -X POST http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-OpenWebUI-Chat-Id: smoke-$(date +%s)" \
  -d '{"model":"helix-consultant","messages":[{"role":"user","content":"Test"}],"stream":false}'
```

{% elif role == 'reviewer' %}
### Reviewer Kriterien

Dein Promise: `CODE_REVIEW_PASSED`

Kriterien:
- [ ] Alle ADR Akzeptanzkriterien erfüllt
- [ ] Alle files.create existieren
- [ ] Alle files.modify wurden geändert
- [ ] Keine Security Issues (Secrets, SQL Injection)

{% elif role == 'dokumentierer' %}
### Dokumentierer Kriterien

Dein Promise: `DOCS_COMPLETE`

Kriterien:
- [ ] files.docs aus ADR aktualisiert
- [ ] Docstrings für alle public APIs
- [ ] ARCHITECTURE-MODULES.md enthält neues Modul

{% endif %}

---

## Deine Aufgabe

**ADR:** `../../adr/{{ adr_file }}`

{{ task_description | default('Lies das ADR und implementiere alle Änderungen.') }}

---

## Status Tracking

Aktualisiere `status.md` nach JEDER Aktion:
- Was hast du gemacht?
- Was ist noch offen?
- Welche Fehler sind aufgetreten?

---

## Completion

Wenn ALLE Kriterien erfüllt sind:

1. Update `status.md` mit finalem Status
2. Git commit (wenn Code geändert)
3. Output: `<promise>{{ completion_promise }}</promise>`

## NIEMALS die Promise ausgeben wenn:

- Deine Rollen-Kriterien nicht erfüllt sind
- Tests fehlschlagen
- Nicht alle ADR-Anforderungen umgesetzt sind

Die Promise ist ein VERSPRECHEN dass alles funktioniert!
```

### 5. Ralph CLI Integration

```python
# src/helix/ralph/controller.py

"""Ralph Controller - Iterative ADR Execution.

Führt ADRs iterativ aus bis das Completion Promise erfüllt ist.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Literal
from enum import Enum


class RalphRole(str, Enum):
    """Verfügbare Rollen für Ralph Automation."""
    DEVELOPER = "developer"
    INTEGRATOR = "integrator"
    REVIEWER = "reviewer"
    DOKUMENTIERER = "dokumentierer"


@dataclass
class RalphConfig:
    """Konfiguration für Ralph Controller."""
    adr_id: str
    adr_file: Path
    role: RalphRole = RalphRole.DEVELOPER
    max_iterations: int = 10
    completion_promise: str = ""
    working_dir: Path = field(default_factory=Path.cwd)

    def __post_init__(self):
        if not self.completion_promise:
            self.completion_promise = f"ADR_{self.adr_id}_COMPLETE"


@dataclass
class RalphResult:
    """Ergebnis einer Ralph Execution."""
    success: bool
    iterations: int
    promise_found: bool
    final_status: str
    errors: list[str] = field(default_factory=list)


STANDARD_PROMISES = {
    RalphRole.DEVELOPER: "UNIT_TESTS_PASSED",
    RalphRole.INTEGRATOR: "INTEGRATION_TEST_PASSED",
    RalphRole.REVIEWER: "CODE_REVIEW_PASSED",
    RalphRole.DOKUMENTIERER: "DOCS_COMPLETE",
}


def get_promise_for_role(role: RalphRole) -> str:
    """Gibt das Standard Completion Promise für eine Rolle zurück.

    Args:
        role: Die Ralph Rolle.

    Returns:
        Das Standard Promise für die Rolle.
    """
    return STANDARD_PROMISES.get(role, "TASK_COMPLETE")
```

---

## Akzeptanzkriterien

### Ralph Section Format

- [ ] Jedes neue ADR mit TOOL|NODE|AGENT|SERVICE|PROCESS hat Ralph Section
- [ ] Ralph Section enthält: Promise, Rollen-Tabelle, Iteration Config
- [ ] ADR-Template (SKILL.md) dokumentiert Ralph Section Format

### Completion Promises

- [ ] Developer: `UNIT_TESTS_PASSED` mit definierten Kriterien
- [ ] Integrator: `INTEGRATION_TEST_PASSED` mit Sub-Agent Test
- [ ] Reviewer: `CODE_REVIEW_PASSED` mit ADR-Validierung
- [ ] Dokumentierer: `DOCS_COMPLETE` mit Docs-Checks

### Sub-Agent Freigabe

- [ ] SubAgentTester Klasse implementiert
- [ ] test_consultant() Methode funktioniert
- [ ] Integration in Controller Template

### Dokumentation

- [ ] docs/RALPH-PATTERN.md erstellt
- [ ] skills/helix/adr/SKILL.md aktualisiert mit Ralph Section
- [ ] templates/controller/CLAUDE.md.j2 erweitert

---

## Konsequenzen

### Positiv

- **Standardisierte ADR-Ausführung** - Jedes ADR folgt dem gleichen Pattern
- **Klare Abschlusskriterien** - Keine Unsicherheit ob fertig
- **Automatische Selbst-Korrektur** - Fehler werden in der Loop behoben
- **Wiederverwendbare Rollen** - Developer, Integrator etc. sind definiert
- **CI/CD Ready** - Promises können automatisch geprüft werden

### Negativ

- **Zusätzliche Komplexität** - Ralph Section muss gepflegt werden
- **Overhead bei kleinen ADRs** - Nicht jedes ADR braucht volle Automation
- **Lernkurve** - Teams müssen Pattern verstehen

### Mitigation

- **Optionale Ralph Section** - Nur für component_type TOOL|NODE|AGENT|SERVICE|PROCESS
- **Einfache Defaults** - Standard-Rollen und -Promises
- **Gute Dokumentation** - RALPH-PATTERN.md erklärt alles

---

## Referenzen

- ADR-025: Sub-Agent Verifikation
- ADR-023: Workflow-Definitionen
- ADR-039: Code Quality Hardening (erstes Ralph-Projekt)
- Geoffrey Huntley's Ralph Wiggum Technique
- templates/controller/CLAUDE.md.j2

---

## Ralph Automation

### Completion Promise

`<promise>ADR_040_COMPLETE</promise>`

### Rollen und Kriterien

| Rolle | Promise | Kriterien |
|-------|---------|-----------|
| Developer | `UNIT_TESTS_PASSED` | Ralph Module erstellt, Tests grün |
| Integrator | `INTEGRATION_TEST_PASSED` | Controller Template funktioniert |
| Dokumentierer | `DOCS_COMPLETE` | RALPH-PATTERN.md, SKILL.md aktualisiert |

### Iteration Config

```yaml
ralph:
  max_iterations: 10
  role: developer
  completion_promise: ADR_040_COMPLETE
  status_file: status.md

  checks:
    - type: files_exist
      files:
        - src/helix/ralph/__init__.py
        - src/helix/ralph/controller.py
        - docs/RALPH-PATTERN.md
    - type: unit_tests
      command: "pytest tests/unit/test_ralph*.py -v"
```
