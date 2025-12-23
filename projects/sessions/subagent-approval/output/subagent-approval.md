# Sub-Agent Freigabe-Konzept

> **Vollständiges Konzept für HELIX v4**
>
> Status: KONZEPT
> Erstellt: 2025-12-23
> Version: 2.0

---

## 1. Konzept-Übersicht

### Das Problem

Wenn eine Claude Code Instanz ein Artefakt erstellt (z.B. ein ADR, Code, Dokumentation), ist die **gleiche Instanz kontaminiert durch den Erstellungsprozess**:

```
Consultant erstellt ADR
    ↓
Consultant prüft eigenes ADR  ← PROBLEMATISCH!
    ↓
"Ja, sieht gut aus"           ← Bestätigungsbias
```

Die Instanz kennt:
- Die Intention hinter Formulierungen
- Implizite Annahmen die nicht dokumentiert wurden
- Was sie "eigentlich meinte" aber nicht schrieb

**Zusätzliche Probleme bei API-Calls:**

1. **Context-Kontamination**: Der Ersteller und Prüfer teilen sich den gleichen "mentalen" Context
2. **Beschränkte Capabilities**: API-Calls haben keine Tool-Nutzung (kein Grep, Read, Bash)
3. **Keine Skill-Nutzung**: Der Prüfer kann keine Skills laden
4. **Starres Prüfschema**: Nur vordefinierte Regeln, keine flexible Interpretation
5. **Kein Codebase-Zugriff**: Kann nicht verifizieren ob referenzierte Dateien existieren

### Die Lösung: Sub-Agenten

```
Phase-Agent (erstellt ADR)
    ↓
spawn_approval_agent()
    ↓
Sub-Agent (FRISCHER Context!)
    ├── Lädt CLAUDE.md mit Prüfanweisungen
    ├── Lädt relevante Skills
    ├── Nutzt alle Tools (Read, Grep, etc.)
    └── Schreibt Ergebnis nach output/
```

**Kernidee:**

> Ein Sub-Agent ist eine neue Claude Code CLI Instanz mit **frischem Context**, die als unabhängiger Prüfer fungiert.

### Warum Sub-Agent besser als API-Call

| Aspekt | Direkter API-Call | Sub-Agent |
|--------|-------------------|-----------|
| **Context** | Kein HELIX-Context | Voller HELIX-Context via CLAUDE.md |
| **Tools** | Keine | Alle Claude Code Tools |
| **Skills** | Nicht ladbar | Kann beliebige Skills laden |
| **Flexibilität** | Statische Regeln | Dynamisch, LLM-gesteuert |
| **Unabhängigkeit** | Teilt Erstellungskontext | Vollständig frischer Context |
| **Tiefe** | Nur explizite Checks | Kann explorativ prüfen |
| **Kosten** | ~1K Tokens | ~10-50K Tokens (volle Instanz) |
| **Latenz** | Millisekunden | Sekunden bis Minuten |
| **Codebase-Zugriff** | Keiner | Voller Zugriff |

**Trade-off:** Höhere Kosten und Latenz für deutlich bessere Prüfqualität.

**Kernvorteil Codebase-Zugriff:**
Der Sub-Agent kann die **Codebase lesen**, um zu prüfen ob:
- Referenzierte Dateien existieren (`files.create`, `files.modify`)
- Implementation realistisch ist
- Bestehende Patterns eingehalten werden
- Keine Konflikte mit existierendem Code entstehen

---

## 2. Architektur-Entscheidungen

### 2.1 Spawn-Mechanismus

**Entscheidung:** Neuer Claude Code Prozess via `subprocess`

```python
# Option A: Direkter Spawn (GEWÄHLT)
subprocess.run([
    "claude", "--print",
    "--dangerously-skip-permissions",
], cwd=approval_dir, input=prompt.encode())

# Option B: Über ClaudeRunner (Alternative)
runner = ClaudeRunner()
result = await runner.run_phase(approval_dir)
```

**Begründung für Option A:**
- Minimale Kopplung an bestehenden Code
- Klare Verantwortungstrennung
- Einfacher zu debuggen und zu testen

### 2.2 Symlink statt Copy

**Entscheidung:** Zu prüfende Dateien werden **symlinked**, nicht kopiert

```python
# Statt: shutil.copy(source, approval_dir / "input" / source.name)
# Besser:
os.symlink(source.absolute(), approval_dir / "input" / source.name)
```

**Begründung:**
- Sub-Agent sieht Original-Pfad für besseres Codebase-Verständnis
- Keine Duplikation
- LSP funktioniert korrekt
- Änderungen am Original werden sofort sichtbar
- Relative Pfade in ADRs bleiben korrekt

### 2.4 Approval-Directory Pattern

**Entscheidung:** Dedizierte Approval-Verzeichnisse unter `approvals/`

```
helix-v4/
├── approvals/              # NEU: Approval-Definitionen
│   ├── adr/               # ADR-Prüfung
│   ├── code/              # Code-Review
│   └── docs/              # Dokumentations-Review
└── ...
```

**Begründung:**
- Zentrale Verwaltung aller Approval-Typen
- Eigene CLAUDE.md pro Approval-Typ
- Versionierbar und testbar

### 2.5 Result-Format

**Entscheidung:** Strukturiertes JSON mit standardisiertem Schema

```json
{
  "approval_id": "uuid",
  "approval_type": "adr",
  "timestamp": "2025-12-23T10:30:00Z",
  "result": "approved" | "rejected" | "needs_revision",
  "confidence": 0.95,
  "findings": [
    {
      "severity": "error" | "warning" | "info",
      "check": "check_name",
      "message": "Beschreibung",
      "location": "optional: Datei/Zeile"
    }
  ],
  "recommendations": ["..."],
  "agent_context": {
    "model": "claude-opus-4-5",
    "duration_seconds": 45.2,
    "tokens_used": 15000
  }
}
```

### 2.6 Integration mit Quality Gates

**Entscheidung:** Neuer Gate-Type `approval` im QualityGateRunner

```python
# quality_gates.py - Erweiterung
async def check_approval(
    self,
    phase_dir: Path,
    approval_type: str,
    files_to_check: list[str]
) -> GateResult:
    """Spawnt Sub-Agent für Approval."""
    runner = ApprovalRunner()
    result = await runner.run_approval(
        approval_type=approval_type,
        input_files=[phase_dir / f for f in files_to_check],
    )
    return GateResult(
        passed=result.approved,
        gate_type="approval",
        message=result.summary,
        details=result.to_dict(),
    )
```

---

## 3. Verzeichnis-Struktur

### 3.1 Approval-Definitionen

```
approvals/
├── README.md                    # Übersicht aller Approval-Typen
│
├── adr/                         # ADR-Prüfung
│   ├── CLAUDE.md               # Instruktionen für Sub-Agent
│   ├── checks/                 # Prüfungsanweisungen
│   │   ├── completeness.md     # Vollständigkeitsprüfung
│   │   ├── migration-plan.md   # Migrationspläne vorhanden?
│   │   ├── acceptance.md       # Akzeptanzkriterien checkbar?
│   │   └── conflicts.md        # Konflikte mit anderen ADRs?
│   ├── skills/                 # Symlinks zu relevanten Skills
│   │   └── adr -> ../../../skills/helix/adr
│   ├── input/                  # Runtime: Zu prüfende Dateien
│   └── output/                 # Runtime: Prüfergebnisse
│
├── code/                        # Code-Review
│   ├── CLAUDE.md
│   ├── checks/
│   │   ├── security.md         # OWASP Top 10
│   │   ├── performance.md      # Performance Anti-Patterns
│   │   ├── tests.md            # Test-Coverage & Quality
│   │   ├── patterns.md         # Design Pattern Compliance
│   │   └── style.md            # Code Style Guidelines
│   └── skills/
│
├── docs/                        # Dokumentations-Review
│   ├── CLAUDE.md
│   ├── checks/
│   │   ├── completeness.md     # Alle Sections vorhanden?
│   │   ├── consistency.md      # Konsistent mit Code?
│   │   └── examples.md         # Beispiele funktional?
│   └── skills/
│
└── architecture/                # Architektur-Review
    ├── CLAUDE.md
    └── checks/
        ├── modularity.md       # Lose Kopplung?
        ├── dependencies.md     # Dependency Graph ok?
        └── patterns.md         # Architektur-Pattern?
```

### 3.2 CLAUDE.md Template für Approvals

```markdown
# Approval: ADR-Prüfung

Du bist ein unabhängiger Prüfer für Architecture Decision Records.

## Deine Aufgabe

1. Lies die zu prüfenden ADRs in `input/`
2. Führe alle Checks in `checks/` durch
3. Schreibe das Ergebnis nach `output/approval-result.json`

## Prüfungen

Für jeden Check in `checks/`:
1. Lies die Check-Beschreibung
2. Prüfe das ADR gegen diese Kriterien
3. Notiere Findings (errors, warnings, infos)

## Output-Format

```json
{
  "result": "approved" | "rejected" | "needs_revision",
  "confidence": 0.0-1.0,
  "findings": [...],
  "recommendations": [...]
}
```

## Wichtig

- Du hast KEINEN Zugriff auf den Erstellungsprozess
- Prüfe objektiv und unvoreingenommen
- Sei konstruktiv in deinen Empfehlungen
- Lies die Skills in `skills/` für Domain-Wissen
```

### 3.3 Check-Datei Beispiel

```markdown
# Check: ADR Vollständigkeit

## Zu prüfende Kriterien

### 1. YAML Header (Pflichtfelder)
- [ ] `adr_id` vorhanden
- [ ] `title` vorhanden
- [ ] `status` vorhanden und gültig

### 2. Sections (alle müssen vorhanden sein)
- [ ] `## Kontext` - Warum diese Änderung?
- [ ] `## Entscheidung` - Was wird entschieden?
- [ ] `## Implementation` - Konkrete Umsetzung
- [ ] `## Dokumentation` - Zu aktualisierende Docs
- [ ] `## Akzeptanzkriterien` - Checkboxen
- [ ] `## Konsequenzen` - Trade-offs

### 3. Inhaltliche Qualität
- [ ] Kontext erklärt das "Warum"
- [ ] Entscheidung ist klar formuliert
- [ ] Implementation enthält konkrete Schritte
- [ ] Mindestens 3 Akzeptanzkriterien
- [ ] Konsequenzen listen Vor- UND Nachteile

## Severity-Mapping

| Kriterium | Bei Fehlen |
|-----------|------------|
| YAML Pflichtfelder | ERROR |
| Pflicht-Sections | ERROR |
| Inhaltliche Qualität | WARNING |
```

---

## 4. Workflow-Integration (phases.yaml)

### 4.1 Neuer Phase-Type: `approval`

```yaml
phases:
  - id: consultant
    type: consultant
    output:
      - output/ADR-feature.md

  - id: approval
    type: approval           # NEU: Spawnt Sub-Agent
    approval_type: adr       # → approvals/adr/
    input:
      - output/ADR-feature.md
    output:
      - output/approval-result.json

  - id: development
    type: development
    depends_on: approval     # Nur wenn approved
    input:
      - output/ADR-feature.md
```

### 4.2 Approval als Quality Gate

Alternative: Approval als Gate statt Phase:

```yaml
phases:
  - id: consultant
    type: consultant
    output:
      - output/ADR-feature.md
    quality_gate:
      type: approval          # NEU
      approval_type: adr
      files:
        - output/ADR-feature.md
      required_result: approved  # approved | needs_revision
```

### 4.3 on_rejection Handler (NEU)

Bei Ablehnung kann ein Feedback-Loop konfiguriert werden:

```yaml
phases:
  - id: consultant
    type: consultant
    output:
      files:
        - output/ADR-feature.md

  - id: approval
    type: approval
    approval_type: adr
    input:
      files:
        - output/ADR-feature.md
    output:
      files:
        - approvals/adr/output/approval-result.json
    quality_gate:
      type: approval_passed
      result_file: approvals/adr/output/approval-result.json
    on_rejection:                   # NEU: Bei Ablehnung
      action: retry_phase           # Wiederholt vorherige Phase
      target_phase: consultant      # Mit Feedback an Consultant
      max_retries: 2                # Max. 2 Überarbeitungen
      feedback_template: |
        ## Freigabe nicht erteilt

        ### Blocking Issues:
        {{blocking_issues}}

        ### Bitte überarbeiten:
        {{suggestions}}
```

**Verfügbare Actions:**
- `retry_phase` - Wiederholt target_phase mit Feedback
- `escalate` - Eskaliert an menschlichen Reviewer
- `fail` - Bricht Workflow ab (Default)

### 4.4 Konfiguration in config/approvals.yaml

```yaml
# config/approvals.yaml

approvals:
  adr:
    enabled: true
    model: claude-opus-4-5    # Hochwertiges Modell für wichtige Prüfungen
    timeout: 300              # 5 Minuten max
    retry_on_failure: true
    required_confidence: 0.8  # Min. Confidence für Auto-Approve

  code:
    enabled: true
    model: claude-sonnet-4-20250514
    timeout: 600
    checks:
      - security
      - tests
      # performance und patterns optional

  docs:
    enabled: false            # Noch nicht implementiert

defaults:
  model: claude-sonnet-4-20250514
  timeout: 300
  retry_on_failure: true
```

---

## 5. Technische Implementation

### 5.1 Modul-Struktur

```
src/helix/
├── approval/                   # NEU: Approval-System
│   ├── __init__.py
│   ├── runner.py              # ApprovalRunner
│   ├── result.py              # ApprovalResult, Finding
│   └── config.py              # ApprovalConfig
│
├── quality_gates.py           # Erweitert um check_approval()
└── orchestrator.py            # Erweitert um approval-Phase
```

### 5.2 ApprovalRunner Implementation

```python
# src/helix/approval/runner.py

"""Sub-Agent Approval Runner for HELIX v4.

Spawns independent Claude Code instances for approval checks.
"""

import asyncio
import json
import os
import shutil
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from .result import ApprovalResult, Finding, Severity


@dataclass
class ApprovalConfig:
    """Configuration for an approval run."""
    approval_type: str
    model: str = "claude-sonnet-4-20250514"
    timeout: int = 300
    retry_on_failure: bool = True
    required_confidence: float = 0.8


class ApprovalRunner:
    """Runs approval checks using sub-agents.

    The ApprovalRunner spawns a new Claude Code CLI instance
    with a fresh context to perform independent validation.

    Example:
        runner = ApprovalRunner()
        result = await runner.run_approval(
            approval_type="adr",
            input_files=[Path("output/ADR-feature.md")],
        )

        if result.approved:
            print("ADR approved!")
        else:
            for finding in result.errors:
                print(f"Error: {finding.message}")
    """

    APPROVALS_DIR = Path("approvals")
    CLAUDE_CMD = "/home/aiuser01/helix-v4/control/claude-wrapper.sh"

    def __init__(
        self,
        approvals_base: Path | None = None,
        claude_cmd: str | None = None,
    ) -> None:
        """Initialize the ApprovalRunner.

        Args:
            approvals_base: Base directory for approval definitions.
            claude_cmd: Path to Claude CLI executable.
        """
        self.approvals_base = approvals_base or self.APPROVALS_DIR
        self.claude_cmd = claude_cmd or self.CLAUDE_CMD

    async def run_approval(
        self,
        approval_type: str,
        input_files: list[Path],
        config: ApprovalConfig | None = None,
    ) -> ApprovalResult:
        """Run an approval check using a sub-agent.

        Args:
            approval_type: Type of approval (e.g., "adr", "code").
            input_files: Files to check.
            config: Optional configuration.

        Returns:
            ApprovalResult with findings and decision.
        """
        config = config or ApprovalConfig(approval_type=approval_type)
        approval_id = str(uuid.uuid4())[:8]

        approval_dir = self.approvals_base / approval_type
        if not approval_dir.exists():
            return ApprovalResult(
                approval_id=approval_id,
                approval_type=approval_type,
                result="rejected",
                confidence=0.0,
                findings=[Finding(
                    severity=Severity.ERROR,
                    check="setup",
                    message=f"Approval type not found: {approval_type}",
                )],
            )

        # Prepare input directory
        input_dir = approval_dir / "input"
        input_dir.mkdir(exist_ok=True)

        # Clean previous inputs (remove old symlinks)
        for old_file in input_dir.iterdir():
            old_file.unlink()

        # Symlink input files (nicht kopieren!)
        # Sub-Agent sieht Original-Pfad für besseres Codebase-Verständnis
        for input_file in input_files:
            if input_file.exists():
                abs_path = input_file.absolute()
                link_path = input_dir / input_file.name
                os.symlink(abs_path, link_path)

        # Build prompt
        prompt = self._build_prompt(approval_type, input_files)

        # Spawn sub-agent
        try:
            result = await self._spawn_agent(
                approval_dir=approval_dir,
                prompt=prompt,
                timeout=config.timeout,
            )
        except asyncio.TimeoutError:
            return ApprovalResult(
                approval_id=approval_id,
                approval_type=approval_type,
                result="rejected",
                confidence=0.0,
                findings=[Finding(
                    severity=Severity.ERROR,
                    check="timeout",
                    message=f"Approval timed out after {config.timeout}s",
                )],
            )

        # Parse result
        output_file = approval_dir / "output" / "approval-result.json"
        if output_file.exists():
            try:
                with open(output_file) as f:
                    result_data = json.load(f)
                return ApprovalResult.from_dict(
                    approval_id=approval_id,
                    approval_type=approval_type,
                    data=result_data,
                )
            except (json.JSONDecodeError, KeyError) as e:
                return ApprovalResult(
                    approval_id=approval_id,
                    approval_type=approval_type,
                    result="rejected",
                    confidence=0.0,
                    findings=[Finding(
                        severity=Severity.ERROR,
                        check="parse",
                        message=f"Failed to parse result: {e}",
                    )],
                )

        return ApprovalResult(
            approval_id=approval_id,
            approval_type=approval_type,
            result="rejected",
            confidence=0.0,
            findings=[Finding(
                severity=Severity.ERROR,
                check="output",
                message="No approval result file generated",
            )],
        )

    async def _spawn_agent(
        self,
        approval_dir: Path,
        prompt: str,
        timeout: int,
    ) -> None:
        """Spawn a sub-agent process.

        Args:
            approval_dir: Working directory for the agent.
            prompt: Prompt to send to the agent.
            timeout: Timeout in seconds.
        """
        cmd = [
            "stdbuf", "-oL", "-eL",
            self.claude_cmd,
            "--print",
            "--dangerously-skip-permissions",
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=approval_dir,
        )

        await asyncio.wait_for(
            process.communicate(input=prompt.encode()),
            timeout=timeout,
        )

    def _build_prompt(
        self,
        approval_type: str,
        input_files: list[Path],
    ) -> str:
        """Build the prompt for the sub-agent.

        Args:
            approval_type: Type of approval.
            input_files: Files being checked.

        Returns:
            Prompt string.
        """
        file_list = ", ".join(f.name for f in input_files)

        return f"""Lies CLAUDE.md und führe eine {approval_type.upper()}-Freigabeprüfung durch.

Zu prüfende Dateien (in input/):
{file_list}

Führe ALLE Checks in checks/ aus und schreibe das Ergebnis nach:
output/approval-result.json

Halte dich strikt an das Output-Format aus CLAUDE.md."""
```

### 5.3 ApprovalResult Dataclass

```python
# src/helix/approval/result.py

"""Result classes for approval checks."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class Severity(Enum):
    """Severity levels for findings."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ApprovalDecision(Enum):
    """Possible approval decisions."""
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"


@dataclass
class Finding:
    """A single finding from an approval check."""
    severity: Severity
    check: str
    message: str
    location: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity.value,
            "check": self.check,
            "message": self.message,
            "location": self.location,
        }


@dataclass
class ApprovalResult:
    """Result of an approval check."""
    approval_id: str
    approval_type: str
    result: str  # "approved", "rejected", "needs_revision"
    confidence: float
    findings: list[Finding] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    duration_seconds: float = 0.0
    tokens_used: int = 0

    @property
    def approved(self) -> bool:
        """Check if the result is approved."""
        return self.result == "approved"

    @property
    def errors(self) -> list[Finding]:
        """Get all error-level findings."""
        return [f for f in self.findings if f.severity == Severity.ERROR]

    @property
    def warnings(self) -> list[Finding]:
        """Get all warning-level findings."""
        return [f for f in self.findings if f.severity == Severity.WARNING]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "approval_id": self.approval_id,
            "approval_type": self.approval_type,
            "result": self.result,
            "confidence": self.confidence,
            "findings": [f.to_dict() for f in self.findings],
            "recommendations": self.recommendations,
            "timestamp": self.timestamp.isoformat(),
            "agent_context": {
                "duration_seconds": self.duration_seconds,
                "tokens_used": self.tokens_used,
            },
        }

    @classmethod
    def from_dict(
        cls,
        approval_id: str,
        approval_type: str,
        data: dict[str, Any],
    ) -> "ApprovalResult":
        """Create from dictionary (parsed from agent output)."""
        findings = [
            Finding(
                severity=Severity(f["severity"]),
                check=f["check"],
                message=f["message"],
                location=f.get("location"),
            )
            for f in data.get("findings", [])
        ]

        return cls(
            approval_id=approval_id,
            approval_type=approval_type,
            result=data.get("result", "rejected"),
            confidence=data.get("confidence", 0.0),
            findings=findings,
            recommendations=data.get("recommendations", []),
        )
```

### 5.4 QualityGateRunner Erweiterung

```python
# Ergänzung zu quality_gates.py

async def check_approval(
    self,
    phase_dir: Path,
    approval_type: str,
    files: list[str],
    required_result: str = "approved",
    config: dict[str, Any] | None = None,
) -> GateResult:
    """Run approval check via sub-agent.

    Args:
        phase_dir: Phase directory.
        approval_type: Type of approval ("adr", "code", etc.).
        files: List of files to check.
        required_result: Required result ("approved" or "needs_revision").
        config: Optional approval configuration.

    Returns:
        GateResult from approval.
    """
    from .approval import ApprovalRunner, ApprovalConfig

    runner = ApprovalRunner()
    input_files = [phase_dir / f for f in files]

    approval_config = None
    if config:
        approval_config = ApprovalConfig(
            approval_type=approval_type,
            model=config.get("model", "claude-sonnet-4-20250514"),
            timeout=config.get("timeout", 300),
        )

    result = await runner.run_approval(
        approval_type=approval_type,
        input_files=input_files,
        config=approval_config,
    )

    passed = (
        result.result == required_result or
        (required_result == "needs_revision" and
         result.result in ("approved", "needs_revision"))
    )

    return GateResult(
        passed=passed,
        gate_type="approval",
        message=f"Approval {result.result} (confidence: {result.confidence:.0%})",
        details=result.to_dict(),
    )
```

---

## 6. Generische Anwendungen

### 6.1 Anwendungs-Matrix

| Approval-Typ | Use Case | Checks | Kosten-Benefit |
|--------------|----------|--------|----------------|
| **adr** | ADR-Freigabe | Vollständigkeit, Konfliktfreiheit, Migration-Plan | HOCH - kritisch für Evolution |
| **code** | Code-Review | Security, Performance, Tests, Patterns | HOCH - Qualitätssicherung |
| **docs** | Doku-Review | Konsistenz, Beispiele, Vollständigkeit | MITTEL - nice-to-have |
| **architecture** | Architektur-Prüfung | Modularität, Dependencies | HOCH - bei großen Änderungen |
| **security** | Security-Audit | OWASP, Credentials, Injection | KRITISCH - immer ausführen |
| **compliance** | Compliance-Check | Lizenz, GDPR, Unternehmensregeln | HOCH - regulatorische Anforderungen |
| **migration** | Migrations-Prüfung | Rollback-Plan, Data-Integrity | HOCH - vor DB-Änderungen |

### 6.2 Prioritäts-Empfehlung

**Phase 1 (MVP):**
- `adr` - Basis für Evolution-System
- `code` - Security-focused

**Phase 2:**
- `docs` - Selbstdokumentation
- `security` - Dedizierter Security-Audit

**Phase 3:**
- `architecture` - Größere Refactorings
- `compliance` - Bei Bedarf

### 6.3 Approval-Kaskaden

Für kritische Änderungen können mehrere Approvals verkettet werden:

```yaml
phases:
  - id: adr-creation
    type: consultant
    output: [output/ADR-critical.md]

  - id: adr-approval
    type: approval
    approval_type: adr
    input: [output/ADR-critical.md]

  - id: implementation
    type: development
    output: [new/src/critical/*.py]

  - id: code-approval
    type: approval
    approval_type: code
    input: [new/src/critical/*.py]

  - id: security-approval
    type: approval
    approval_type: security
    input: [new/src/critical/*.py]
```

---

## 7. Vergleich mit anderen Ansätzen

### 7.1 Sub-Agent vs. API-Call vs. Hybrid

| Kriterium | API-Call | Sub-Agent | Hybrid |
|-----------|----------|-----------|--------|
| **Latenz** | ~100ms | ~30-60s | ~5-30s |
| **Kosten** | ~$0.01 | ~$0.10-0.50 | ~$0.05-0.20 |
| **Tiefe** | Oberflächlich | Tiefgehend | Konfigurierbar |
| **Context** | Kontaminiert | Frisch | Teilweise frisch |
| **Tools** | Keine | Alle | Begrenzt |
| **Komplexität** | Gering | Hoch | Mittel |

### 7.2 Wann welchen Ansatz?

```
┌─────────────────────────────────────────────────────────────────┐
│                    Entscheidungsbaum                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Ist es ein kritischer Check?                                   │
│      │                                                          │
│      ├── JA → Sub-Agent (volle Prüftiefe)                      │
│      │                                                          │
│      └── NEIN → Ist der Check deterministisch?                 │
│                    │                                            │
│                    ├── JA → API-Call (schnell, günstig)        │
│                    │                                            │
│                    └── NEIN → Braucht der Check Tools?         │
│                                  │                              │
│                                  ├── JA → Sub-Agent            │
│                                  │                              │
│                                  └── NEIN → Hybrid             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 7.3 Hybrid-Ansatz für Kosten-Optimierung

```python
async def smart_approval(files: list[Path], approval_type: str) -> ApprovalResult:
    """Intelligenter Approval mit Fallback."""

    # Phase 1: Schneller API-Check (deterministisch)
    quick_result = await quick_api_check(files, approval_type)

    if quick_result.has_critical_errors:
        # Sofort ablehnen ohne Sub-Agent
        return quick_result

    if quick_result.all_clear and quick_result.confidence > 0.95:
        # Schnell durchwinken wenn offensichtlich ok
        return quick_result

    # Phase 2: Sub-Agent für tiefgehende Prüfung
    return await spawn_approval_agent(files, approval_type)
```

---

## 8. Empfehlung & Roadmap

### 8.1 Architektur-Empfehlung

**Empfohlen: Hybrid-Ansatz mit Sub-Agent-Fallback**

```
┌─────────────────────────────────────────────────────────────────┐
│                    Approval-Pipeline                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Input Files                                                    │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────────┐                                           │
│  │ Quick Validator │ ← Deterministisch (API-Call)              │
│  │ - Syntax        │   ~100ms, ~$0.01                          │
│  │ - Schema        │                                            │
│  │ - Required      │                                            │
│  └────────┬────────┘                                           │
│           │                                                     │
│     ┌─────┴─────┐                                              │
│     │ Errors?   │                                               │
│     └─────┬─────┘                                              │
│      YES  │  NO                                                 │
│       │   │                                                     │
│       ▼   ▼                                                     │
│    REJECT ┌─────────────────┐                                  │
│           │ Sub-Agent Check │ ← LLM-basiert                    │
│           │ - Semantik      │   ~30s, ~$0.20                   │
│           │ - Konflikte     │                                   │
│           │ - Tiefenanalyse │                                   │
│           └────────┬────────┘                                   │
│                    │                                            │
│                    ▼                                            │
│            APPROVED / REJECTED / NEEDS_REVISION                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 8.2 Implementierungs-Roadmap

#### Phase 1: Foundation
- [ ] Erstelle `approvals/` Verzeichnisstruktur
- [ ] Implementiere `ApprovalRunner` und `ApprovalResult`
- [ ] Erstelle `approvals/adr/` mit CLAUDE.md und Checks
- [ ] Integration in `QualityGateRunner.check_approval()`
- [ ] Unit Tests für Runner und Result

#### Phase 2: Integration
- [ ] Erweitere `phases.yaml` Schema um `type: approval`
- [ ] Orchestrator-Support für Approval-Phasen
- [ ] Implementiere `on_rejection` Handler
- [ ] Logging und Observability
- [ ] E2E-Test: ADR erstellen → Approval → Weiterverarbeitung

#### Phase 3: Erweiterung
- [ ] Code-Approval (`approvals/code/`)
- [ ] Docs-Approval (`approvals/docs/`)
- [ ] Hybrid-Ansatz mit Quick-Validator
- [ ] Retry-Logik bei Approval-Fehlern

#### Phase 4: Optimierung
- [ ] Kosten-Tracking pro Approval
- [ ] Caching für wiederkehrende Checks
- [ ] Parallelisierung mehrerer Approvals
- [ ] Metriken: Approval-Rate, Durchlaufzeit, Kosten

### 8.3 Quick Wins (sofort umsetzbar)

1. **approvals/adr/ Verzeichnis** anlegen mit CLAUDE.md und checks/
2. **Manueller Test** mit:
   ```bash
   cd approvals/adr
   ln -sf ../../projects/evolution/feature/output/ADR-feature.md input/
   claude -p "Lies CLAUDE.md und führe Freigabeprüfung aus"
   ```
3. **ApprovalRunner** Basisversion implementieren
4. **ADR-Prüfung** als Proof of Concept durchführen

### 8.4 Erfolgs-Metriken

| Metrik | Ziel | Messung |
|--------|------|---------|
| Approval-Latenz | < 60s | Timer im Runner |
| Approval-Kosten | < $0.30 | Token-Tracking |
| False-Positive-Rate | < 5% | Manuelle Review |
| False-Negative-Rate | < 1% | Post-Deployment Issues |
| Approval-Coverage | > 90% | ADRs mit Approval / Alle ADRs |

---

## 9. Zusammenfassung

### Kernaussagen

1. **Sub-Agenten bieten frischen Context** - kritisch für unvoreingenommene Prüfung
2. **Höhere Kosten, aber deutlich bessere Qualität** - Trade-off zugunsten Qualität
3. **Generisches Pattern** - nicht nur für ADRs, sondern für alle Freigaben
4. **Hybrid-Ansatz optimal** - Schnelle deterministische Checks + Sub-Agent für Tiefe

### Nächste Schritte

1. Review dieses Konzepts durch User
2. ADR erstellen (ADR-015: Sub-Agent Approval System)
3. Implementierung Phase 1 starten

---

## 10. Appendix

### A. Vollständiger ADR Approval Flow (Beispiel)

```bash
# 1. Consultant erstellt ADR
cd projects/evolution/new-feature
claude -p "Erstelle ein ADR für Feature X"
# → output/ADR-feature-x.md

# 2. Sub-Agent prüft ADR
cd ../../../approvals/adr
ln -sf ../../projects/evolution/new-feature/output/ADR-feature-x.md input/
claude -p "Lies CLAUDE.md und führe Freigabeprüfung aus"
# → output/approval-result.json

# 3. Ergebnis prüfen
cat output/approval-result.json | jq .result
# "approved" → Weiter mit Implementation
# "rejected" → Feedback an Consultant
```

### B. JSON Schema für approval-result.json

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["result", "confidence", "findings"],
  "properties": {
    "approval_id": { "type": "string" },
    "approval_type": { "type": "string" },
    "result": {
      "type": "string",
      "enum": ["approved", "rejected", "needs_revision"]
    },
    "confidence": {
      "type": "number",
      "minimum": 0,
      "maximum": 1
    },
    "findings": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["severity", "check", "message"],
        "properties": {
          "severity": { "enum": ["error", "warning", "info"] },
          "check": { "type": "string" },
          "message": { "type": "string" },
          "location": { "type": "string" }
        }
      }
    },
    "recommendations": {
      "type": "array",
      "items": { "type": "string" }
    },
    "agent_context": {
      "type": "object",
      "properties": {
        "model": { "type": "string" },
        "duration_seconds": { "type": "number" },
        "tokens_used": { "type": "integer" }
      }
    }
  }
}
```

### C. Risiken & Mitigationen

| Risiko | Wahrscheinlichkeit | Mitigation |
|--------|-------------------|------------|
| Hohe Kosten | Mittel | Timeout + Caching + Hybrid-Ansatz |
| Langsame Execution | Mittel | Parallele Approvals + Quick-Validator |
| Inkonsistente Results | Niedrig | Deterministische Checks first |
| Sub-Agent Fehler | Mittel | Retry-Logik + Fallback |
| Context-Leak | Niedrig | Strikte Verzeichnis-Isolation |

---

*Erstellt: 2025-12-23 | HELIX v4 Sub-Agent Freigabe-Konzept v2.0*
