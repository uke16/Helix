# ARCHITECTURE-ORCHESTRATOR-FULL.md

> Vollständige Architektur-Dokumentation für den HELIX Phase Orchestrator
>
> Stand: 2025-12-23
> Autor: HELIX Consultant Session

---

## Übersicht

Dieses Dokument beschreibt die vollständige Orchestrator-Architektur in zwei Teilen:

1. **Teil 1: MVP** - Was sofort implementiert wird (ADR-017)
2. **Teil 2-5: MaxVP** - Erweiterte Features für später

```
┌─────────────────────────────────────────────────────────────────┐
│                    HELIX ORCHESTRATOR                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  MVP (Teil 1)                MaxVP (Teil 2-5)                   │
│  ────────────                ────────────────                   │
│  • Basis-Orchestrator        • Domain Consultants               │
│  • Linearer Datenfluss       • Hardware-Tool Integration        │
│  • Feste Quality Gates       • Projekt-Hierarchie               │
│  • CLI & API                 • Parallele Ausführung             │
│  • Status-Tracking           • DAG Dependencies                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

# Teil 1: MVP - Basis-Orchestrator

> **Scope:** Was in ADR-017 definiert ist
> **Aufwand:** 2 Wochen

## 1.1 Kern-Architektur

### Modulare Struktur

```
src/helix/
├── orchestrator/                    # Neues Orchestrator-Paket
│   ├── __init__.py                  # Exports
│   ├── runner.py                    # OrchestratorRunner (Hauptklasse)
│   ├── phase_executor.py            # PhaseExecutor
│   ├── data_flow.py                 # DataFlowManager
│   └── status.py                    # StatusTracker
│
├── orchestrator.py                  # Existierend: Basis-Klasse
│
└── cli/
    ├── __init__.py                  # Erweitern
    └── project.py                   # NEU: project-Subcommands
```

### Komponenten-Überblick

```
┌─────────────────────────────────────────────────────────────────┐
│                    OrchestratorRunner                           │
│                    ─────────────────                            │
│  • Lädt phases.yaml                                             │
│  • Koordiniert Phasen-Ausführung                                │
│  • Handhabt Failures und Retries                                │
│  • Resume-Fähigkeit nach Neustart                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │  PhaseExecutor  │  │  DataFlowManager │  │  StatusTracker  │  │
│  │  ─────────────  │  │  ──────────────  │  │  ────────────   │  │
│  │  • Claude CLI   │  │  • Kopiert       │  │  • status.yaml  │  │
│  │  • Gate Check   │  │    outputs →     │  │  • Phase-Status │  │
│  │  • Retry Logic  │  │    inputs        │  │  • Timestamps   │  │
│  │  • Timeout      │  │  • Projekt-Files │  │  • Fehler-Log   │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 1.2 Projekt-Typen

Der Consultant bestimmt den Projekt-Typ bei Erstellung:

```yaml
# config/phase-types.yaml

project_types:
  simple:
    description: "Standard-Feature (Schema F)"
    default_phases:
      - consultant
      - development
      - review
      - integration
    auto_approve: false

  complex:
    description: "Komplexes Feature mit Feasibility"
    default_phases:
      - consultant
      - feasibility
      - planning
      - development
      - review
      - integration
    auto_approve: false

  exploratory:
    description: "Exploration ohne festen Plan"
    default_phases:
      - consultant
      - research
      - decision
    auto_approve: false
```

### Workflow-Diagramm: Simple

```
┌───────────────┐     ┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│  CONSULTANT   │────▶│  DEVELOPMENT  │────▶│    REVIEW     │────▶│  INTEGRATION  │
│               │     │               │     │               │     │               │
│  Output:      │     │  Output:      │     │  Output:      │     │  Output:      │
│  • ADR.md     │     │  • src/*.py   │     │  • approved   │     │  • merged     │
│  • spec.yaml  │     │  • tests/*.py │     │               │     │               │
│               │     │               │     │               │     │               │
│  Gate:        │     │  Gate:        │     │  Gate:        │     │  Gate:        │
│  adr_valid    │     │  tests_pass   │     │  review_ok    │     │  all_tests    │
└───────────────┘     └───────────────┘     └───────────────┘     └───────────────┘
```

### Workflow-Diagramm: Complex

```
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│  CONSULTANT   │────▶│  FEASIBILITY  │────▶│   PLANNING    │
│               │     │               │     │               │
│  Output:      │     │  Output:      │     │  Output:      │
│  • ADR.md     │     │  • poc/       │     │  • plan.yaml  │
│  • spec.yaml  │     │  • findings   │     │  • new phases │
│               │     │               │     │               │
│  Gate:        │     │  Gate:        │     │  Gate:        │
│  adr_valid    │     │  poc_working  │     │  plan_valid   │
└───────────────┘     └───────────────┘     └───────┬───────┘
                                                    │
        ┌───────────────────────────────────────────┘
        │
        ▼
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│  DEVELOPMENT  │────▶│    REVIEW     │────▶│  INTEGRATION  │
│               │     │               │     │               │
│  (dynamisch   │     │               │     │               │
│   aus plan)   │     │               │     │               │
└───────────────┘     └───────────────┘     └───────────────┘
```

## 1.3 Datenfluss zwischen Phasen

### Automatisches Kopieren

```
Phase A (consultant)              Phase B (development)
────────────────────              ─────────────────────
output/                           input/
├── ADR-feature.md    ──COPY──▶   ├── ADR-feature.md
├── spec.yaml         ──COPY──▶   ├── spec.yaml
└── requirements.md   ──COPY──▶   └── requirements.md
```

### DataFlowManager Implementation

```python
class DataFlowManager:
    """Kopiert Outputs automatisch als Inputs."""

    async def prepare_phase_inputs(
        self,
        project_dir: Path,
        phase: PhaseConfig,
        status: ProjectStatus,
    ) -> None:
        """Kopiert relevante Outputs als Inputs."""

        input_from = phase.config.get("input_from", [])
        phase_dir = project_dir / "phases" / phase.id
        input_dir = phase_dir / "input"

        for source_phase_id in input_from:
            source_dir = project_dir / "phases" / source_phase_id / "output"
            self._copy_outputs(source_dir, input_dir)

        # Projekt-Level Dateien (spec.yaml, ADRs)
        self._copy_project_files(project_dir, input_dir)
```

## 1.4 Quality Gates

### Feste Gates pro Phase-Type

```yaml
# config/phase-types.yaml

phase_types:
  consultant:
    default_gates:
      - adr_valid
    output_pattern: "output/ADR-*.md"

  development:
    default_gates:
      - files_exist
      - syntax_check
      - tests_pass
    output_pattern: "output/src/**/*.py"

  review:
    default_gates:
      - review_approved
    requires_input_from: [development, consultant]

  integration:
    default_gates:
      - all_tests_pass
      - docs_current
    requires_input_from: [development, review]
```

### Gate-Überschreibung in phases.yaml

```yaml
# phases.yaml - Custom Gates
phases:
  - id: development
    type: development
    quality_gate:
      type: compound
      gates:
        - syntax_check
        - tests_pass
        - coverage_min: 80  # Custom Parameter
```

## 1.5 Status-Tracking

### status.yaml Format

```yaml
# status.yaml - vom Orchestrator gepflegt
project_id: my-feature
status: in_progress
total_phases: 4
completed_phases: 2
started_at: 2025-12-23T10:00:00
completed_at: null
error: null

phases:
  consultant:
    status: completed
    started_at: 2025-12-23T10:00:00
    completed_at: 2025-12-23T10:05:00
    retries: 0

  development:
    status: in_progress
    started_at: 2025-12-23T10:06:00
    completed_at: null
    retries: 1
    error: "tests_pass failed"

  review:
    status: pending

  integration:
    status: pending
```

### Resume nach Fehler

```bash
# Projekt läuft, dann Fehler in development
helix project run my-feature
# → Fehler: tests_pass failed

# Entwickler fixt den Bug manuell

# Resume ab letzter Phase
helix project run my-feature --resume
# → Startet wieder bei development
```

## 1.6 CLI Integration

```bash
# Projekt erstellen
helix project create my-feature --type simple

# Projekt ausführen
helix project run my-feature

# Status prüfen
helix project status my-feature

# Nach Fehler fortsetzen
helix project run my-feature --resume

# Dry-Run (zeigt was passieren würde)
helix project run my-feature --dry-run

# Alle Projekte auflisten
helix project list
```

## 1.7 API Integration

```python
# POST /project/{name}/run
{
  "resume": false,
  "dry_run": false
}
# → {"status": "started", "project": "my-feature"}

# GET /project/{name}/status
# → {"status": "running", "phases": {...}}

# GET /projects
# → [{"name": "my-feature", "status": "running"}]
```

---

# Teil 2: MaxVP - Domain Consultants

> **Konzept aus ADR-005:** Domain Consultants sind Sub-Agenten vom Haupt-Consultant
> **Aufwand:** 2-3 Wochen nach MVP

## 2.1 Architektur-Überblick

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER                                    │
│  "Baue BOM-Export der auch SAP-Daten enthält"                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    META-CONSULTANT                              │
│                    ───────────────                              │
│  • Analysiert Request                                           │
│  • Erkennt Keywords: "BOM" → PDM, "SAP" → ERP                   │
│  • Wählt Domain-Experten                                        │
│  • Ruft Sub-Agenten auf                                         │
│  • Synthetisiert Ergebnisse                                     │
│  • Schreibt ADR + spec.yaml                                     │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│  PDM EXPERT   │     │  ERP EXPERT   │     │ INFRA EXPERT  │
│  ───────────  │     │  ──────────   │     │ ────────────  │
│  Sub-Agent    │     │  Sub-Agent    │     │  Sub-Agent    │
│  Liest:       │     │  Liest:       │     │  Liest:       │
│  skills/pdm/  │     │  skills/erp/  │     │  skills/infra/│
│               │     │               │     │               │
│  Output:      │     │  Output:      │     │  Output:      │
│  analysis.json│     │  analysis.json│     │  analysis.json│
└───────────────┘     └───────────────┘     └───────────────┘
```

## 2.2 Domain-Experten Konfiguration

```yaml
# config/domain-experts.yaml

experts:
  pdm:
    name: "PDM Domain Expert"
    description: "Produktdatenmanagement, Stücklisten, Revisionen"
    skills:
      - "skills/pdm/structure.md"
      - "skills/pdm/bom.md"
      - "skills/pdm/revisions.md"
    triggers:
      - "stückliste"
      - "bom"
      - "revision"
      - "artikel"
      - "produkt"

  erp:
    name: "ERP Integration Expert"
    description: "SAP-Integration, Aufträge, Bestellungen"
    skills:
      - "skills/erp/integration.md"
      - "skills/erp/orders.md"
    triggers:
      - "sap"
      - "auftrag"
      - "bestellung"

  encoder:
    name: "Encoder Domain Expert"
    description: "Drehgeber, Sensoren, Firmware"
    skills:
      - "skills/encoder/hardware.md"
      - "skills/encoder/firmware.md"
      - "skills/encoder/canopen.md"
    triggers:
      - "drehgeber"
      - "encoder"
      - "sensor"
      - "canopen"
      - "firmware"

  infrastructure:
    name: "Infrastructure Expert"
    description: "Deployment, Docker, CI/CD"
    skills:
      - "skills/infrastructure/docker.md"
      - "skills/infrastructure/kubernetes.md"
    triggers:
      - "deploy"
      - "docker"
      - "kubernetes"
```

## 2.3 Meeting-Ablauf

### Phase 1: Request-Analyse

```
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 1: Request-Analyse (Meta-Consultant)                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Input: "Baue CAN-Open Drehgeber Firmware für neue Hardware"    │
│                                                                 │
│  Meta-Consultant analysiert:                                    │
│  1. Keywords: "CAN-Open" → encoder, "Firmware" → encoder        │
│  2. Implizit: Hardware-Test nötig                               │
│  3. Wählt Experten: [encoder, infrastructure]                   │
│                                                                 │
│  Output: expert-selection.json                                  │
│  {                                                              │
│    "experts": ["encoder", "infrastructure"],                    │
│    "questions": {                                               │
│      "encoder": "Welche Sensor-Schnittstellen sind relevant?",  │
│      "infrastructure": "Wie wird die Firmware deployed?"        │
│    }                                                            │
│  }                                                              │
└─────────────────────────────────────────────────────────────────┘
```

### Phase 2: Parallel-Analyse

```
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 2: Experten-Analyse (Parallel via Claude Code CLI)       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Encoder-Expert                   Infrastructure-Expert         │
│  ──────────────                   ─────────────────────         │
│  $ claude -p "..." \              $ claude -p "..." \           │
│    --cwd phases/01/meeting/         --cwd phases/01/meeting/    │
│           encoder-expert/                  infra-expert/        │
│                                                                 │
│  Liest:                           Liest:                        │
│  • skills/encoder/*               • skills/infrastructure/*     │
│  • Frage vom Meta                 • Frage vom Meta              │
│                                                                 │
│  Schreibt:                        Schreibt:                     │
│  output/analysis.json             output/analysis.json          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Phase 3: Synthese

```
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 3: Synthese (Meta-Consultant)                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Meta-Consultant liest alle analysis.json                       │
│                                                                 │
│  Prüft auf:                                                     │
│  • Konflikte (z.B. widersprüchliche Anforderungen)              │
│  • Lücken (z.B. fehlende Info über Hardware)                    │
│  • Dependencies (z.B. Firmware braucht HAL zuerst)              │
│                                                                 │
│  Bei Unklarheiten:                                              │
│  → Rückfrage an User                                            │
│                                                                 │
│  Output: synthesis.json                                         │
│  {                                                              │
│    "combined_requirements": [...],                              │
│    "conflicts_resolved": [...],                                 │
│    "recommended_phases": [                                      │
│      "feasibility",                                             │
│      "hal-development",                                         │
│      "canopen-stack",                                           │
│      "hil-test"                                                 │
│    ]                                                            │
│  }                                                              │
└─────────────────────────────────────────────────────────────────┘
```

## 2.4 Verzeichnis-Struktur für Meetings

```
phases/01-consultant/
├── CLAUDE.md                        # Meta-Consultant Prompt
│
├── input/
│   └── request.md                   # Original User-Request
│
├── meeting/
│   ├── phase-1-selection/
│   │   └── expert-selection.json
│   │
│   ├── phase-2-analysis/
│   │   ├── encoder-expert/
│   │   │   ├── CLAUDE.md            # Expert-spezifischer Prompt
│   │   │   ├── skills/              # Symlinks zu Domain-Skills
│   │   │   └── output/
│   │   │       └── analysis.json
│   │   │
│   │   └── infra-expert/
│   │       ├── CLAUDE.md
│   │       ├── skills/
│   │       └── output/
│   │           └── analysis.json
│   │
│   └── phase-3-synthesis/
│       └── synthesis.json
│
├── output/
│   ├── ADR-canopen-encoder.md
│   ├── spec.yaml
│   └── phases.yaml
│
└── logs/
    └── meeting-transcript.md
```

## 2.5 Implementation: ConsultantMeeting

```python
# src/helix/orchestrator/consultant_meeting.py

class ConsultantMeeting:
    """Orchestriert Domain-Experten Meetings."""

    def __init__(self, experts_config: Path):
        self.experts = self._load_experts(experts_config)

    async def run(
        self,
        project_dir: Path,
        user_request: str,
    ) -> ConsultantOutput:
        """Führt vollständiges Meeting durch."""

        consultant_dir = project_dir / "phases" / "01-consultant"

        # Phase 1: Experten auswählen
        selection = await self._select_experts(user_request)

        # Phase 2: Experten parallel analysieren
        analyses = await self._run_expert_analyses(
            consultant_dir,
            selection,
            user_request,
        )

        # Phase 3: Synthese
        synthesis = await self._synthesize(analyses, user_request)

        # Phase 4: Output generieren
        return await self._generate_output(synthesis)

    async def _run_expert_analyses(
        self,
        consultant_dir: Path,
        selection: dict,
        user_request: str,
    ) -> dict[str, dict]:
        """Führt Experten-Analysen parallel aus."""

        tasks = []
        for expert_id in selection["experts"]:
            expert_dir = consultant_dir / "meeting" / "phase-2-analysis" / f"{expert_id}-expert"

            # Verzeichnis vorbereiten
            await self._setup_expert_dir(
                expert_dir,
                self.experts[expert_id],
                selection["questions"][expert_id],
            )

            # Claude Code CLI Task
            task = asyncio.create_task(
                self._run_claude_expert(expert_dir)
            )
            tasks.append((expert_id, task))

        # Parallel ausführen
        results = {}
        for expert_id, task in tasks:
            results[expert_id] = await task

        return results
```

---

# Teil 3: MaxVP - Hardware-Tool Integration

> **Kern-Insight:** Hardware-Tools sind generisch: VPN → SSH → Python → Library
> **Aufwand:** 2-3 Wochen

## 3.1 Generic Pattern

```
┌─────────────────────────────────────────────────────────────────┐
│                    HARDWARE-TOOL PATTERN                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Claude Code CLI (lokal)                                        │
│        │                                                        │
│        │ VPN                                                    │
│        ▼                                                        │
│  Lab-Server (192.168.x.x)                                       │
│        │                                                        │
│        │ SSH                                                    │
│        ▼                                                        │
│  Python Environment                                             │
│        │                                                        │
│        │ Library                                                │
│        ▼                                                        │
│  Hardware (JTAG, Scope, etc.)                                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 3.2 Skill-Format für Tools

```
skills/tools/jtag/
├── SKILL.md              # Dokumentation für Claude
├── examples/             # Code-Beispiele
│   ├── flash_firmware.py
│   ├── read_memory.py
│   └── debug_session.py
├── requirements.txt      # pyocd, jlink, etc.
└── setup.md              # Hardware-Setup Anleitung
```

### SKILL.md für JTAG

```markdown
# JTAG Debugger Tool

## Übersicht

Dieses Tool ermöglicht Debugging und Flashing von Microcontrollern.

## Verfügbare Operationen

| Operation | Beschreibung | Beispiel |
|-----------|--------------|----------|
| flash | Firmware flashen | `pyocd flash firmware.bin` |
| reset | MCU zurücksetzen | `pyocd reset` |
| halt | MCU anhalten | `pyocd halt` |
| read_mem | Speicher lesen | `pyocd read32 0x20000000` |

## Python API

```python
from pyocd.core.helpers import ConnectHelper

# Verbindung herstellen
session = ConnectHelper.session_with_chosen_probe()
target = session.target

# Firmware flashen
from pyocd.flash.file_programmer import FileProgrammer
FileProgrammer(session).program("firmware.bin")

# Speicher lesen
data = target.read_memory(0x20000000, 256)
```

## Verwendung in HELIX

Claude Code CLI kann diese Tools über SSH nutzen:

```bash
ssh lab-server "cd /project && python -m tools.jtag flash firmware.bin"
```

## Troubleshooting

- **Probe nicht gefunden:** USB-Verbindung prüfen
- **Permission denied:** udev-Rules installieren
- **Flash failed:** Target-Power prüfen
```

## 3.3 Oscilloscope Tool

```
skills/tools/oscilloscope/
├── SKILL.md
├── examples/
│   ├── capture_waveform.py
│   ├── measure_frequency.py
│   └── screenshot.py
└── requirements.txt      # pyvisa, etc.
```

### SKILL.md für Oscilloscope

```markdown
# Oscilloscope Tool

## Übersicht

Rigol DS1054Z Oszilloskop über VISA/LAN.

## Python API

```python
import pyvisa

# Verbindung
rm = pyvisa.ResourceManager()
scope = rm.open_resource('TCPIP::192.168.1.100::INSTR')

# Screenshot
scope.write(':DISP:DATA? ON,OFF,PNG')
data = scope.read_raw()
with open('screenshot.png', 'wb') as f:
    f.write(data[11:])

# Messung
freq = scope.query(':MEAS:FREQ? CHAN1')
print(f"Frequenz: {freq} Hz")
```

## Verwendung in HIL-Tests

```python
async def test_pwm_frequency():
    """Prüft PWM-Ausgabe des Encoders."""

    # Encoder starten
    await jtag.flash("encoder_firmware.bin")
    await jtag.reset()

    # Warten auf Initialisierung
    await asyncio.sleep(0.5)

    # Frequenz messen
    freq = await scope.measure_frequency(channel=1)

    assert 900 < freq < 1100, f"PWM frequency {freq}Hz out of range"
```
```

## 3.4 Tool-Aufruf aus Phase

```yaml
# phases.yaml für Hardware-Projekt

phases:
  - id: hil-test
    type: hardware-test
    tools:
      - jtag
      - oscilloscope

    # SSH-Konfiguration
    ssh:
      host: lab-server.local
      user: helix
      key: ~/.ssh/lab_key

    # Test-Skript
    script: |
      cd /project/tests
      python -m pytest test_hil.py -v

    quality_gate:
      type: tests_pass
```

### PhaseExecutor mit SSH

```python
class PhaseExecutor:

    async def execute_hardware_phase(
        self,
        phase_dir: Path,
        phase_config: PhaseConfig,
    ) -> PhaseResult:
        """Führt Hardware-Phase via SSH aus."""

        ssh_config = phase_config.config.get("ssh", {})

        # SSH-Verbindung
        async with asyncssh.connect(
            ssh_config["host"],
            username=ssh_config["user"],
            client_keys=[ssh_config["key"]],
        ) as conn:

            # Projekt-Dateien kopieren
            await conn.run(f"mkdir -p /tmp/helix/{phase_config.id}")

            async with conn.start_sftp_client() as sftp:
                await sftp.put(
                    phase_dir / "output",
                    f"/tmp/helix/{phase_config.id}/",
                    recurse=True,
                )

            # Test-Skript ausführen
            result = await conn.run(
                phase_config.config.get("script", ""),
                check=False,
            )

            return PhaseResult(
                phase_id=phase_config.id,
                success=result.returncode == 0,
                started_at=datetime.now(),
                completed_at=datetime.now(),
                error=result.stderr if result.returncode != 0 else None,
            )
```

## 3.5 MCP-Server Alternative (Optional)

Für komplexere Tool-Integration kann ein MCP-Server verwendet werden:

```python
# tools/jtag/mcp_server.py

from mcp import Server, Tool

server = Server("jtag-tools")

@server.tool()
async def flash_firmware(firmware_path: str) -> str:
    """Flash firmware to target MCU."""
    from pyocd.flash.file_programmer import FileProgrammer

    session = ConnectHelper.session_with_chosen_probe()
    FileProgrammer(session).program(firmware_path)

    return f"Flashed {firmware_path} successfully"

@server.tool()
async def read_memory(address: int, length: int) -> list[int]:
    """Read memory from target."""
    session = ConnectHelper.session_with_chosen_probe()
    data = session.target.read_memory(address, length)
    return list(data)
```

```yaml
# claude-code-config für Hardware-Projekte
mcp_servers:
  jtag:
    command: python
    args: ["-m", "tools.jtag.mcp_server"]
  oscilloscope:
    command: python
    args: ["-m", "tools.oscilloscope.mcp_server"]
```

---

# Teil 4: MaxVP - Projekt-Hierarchie

> **Konzept:** Sub-Projekte für große Features
> **Aufwand:** 2 Wochen

## 4.1 Hierarchie-Struktur

```
projects/
└── canopen-encoder/                    # Haupt-Projekt
    ├── project.yaml                    # Projekt-Metadaten
    ├── status.yaml                     # Aggregierter Status
    │
    └── sub-projects/
        ├── feasibility/                # Sub-Projekt 1
        │   ├── project.yaml
        │   ├── phases.yaml
        │   ├── status.yaml
        │   └── phases/
        │       └── poc/
        │
        ├── hal-layer/                  # Sub-Projekt 2
        │   ├── project.yaml
        │   ├── phases.yaml
        │   ├── status.yaml
        │   └── phases/
        │
        ├── canopen-stack/              # Sub-Projekt 3
        │   └── ...
        │
        └── hil-test/                   # Sub-Projekt 4
            └── ...
```

## 4.2 Status-Aggregation

```yaml
# canopen-encoder/status.yaml (Haupt-Projekt)

project_id: canopen-encoder
status: in_progress
started_at: 2025-12-20T09:00:00

sub_projects:
  feasibility:
    status: completed
    completed_at: 2025-12-20T14:00:00

  hal-layer:
    status: completed
    completed_at: 2025-12-21T16:00:00

  canopen-stack:
    status: in_progress
    progress: 2/4 phases

  hil-test:
    status: pending
    blocked_by: canopen-stack

aggregated:
  total_phases: 12
  completed_phases: 7
  estimated_remaining: "2-3 days"
```

## 4.3 Visualisierung

```
┌─────────────────────────────────────────┐
│ PROJECT: canopen-encoder                │
│ Status: in_progress (58%)               │
│                                         │
│ Sub-Projects:                           │
│ ├── feasibility/  [████████████] 100%   │
│ │   └── poc-sensor-reading ✅            │
│ │                                       │
│ ├── hal-layer/    [████████████] 100%   │
│ │   ├── gpio-driver ✅                   │
│ │   ├── spi-driver ✅                    │
│ │   └── timer-driver ✅                  │
│ │                                       │
│ ├── canopen-stack/ [██████░░░░░░] 50%   │
│ │   ├── nmt-handler ✅                   │
│ │   ├── sdo-server ✅                    │
│ │   ├── pdo-mapping 🔄                   │
│ │   └── eds-generator ⏳                 │
│ │                                       │
│ └── hil-test/     [░░░░░░░░░░░░] 0%     │
│     └── (blocked by canopen-stack)      │
│                                         │
└─────────────────────────────────────────┘
```

## 4.4 Sub-Projekt Dependencies

```yaml
# canopen-encoder/project.yaml

project:
  name: canopen-encoder
  type: complex

sub_projects:
  - id: feasibility
    type: feasibility

  - id: hal-layer
    type: development
    depends_on: [feasibility]

  - id: canopen-stack
    type: development
    depends_on: [hal-layer]

  - id: hil-test
    type: hardware-test
    depends_on: [canopen-stack]

# Orchestrator startet hal-layer erst wenn feasibility complete
```

## 4.5 Shared Context zwischen Sub-Projekten

```
canopen-encoder/
├── shared/                        # Geteilte Artefakte
│   ├── spec.yaml                  # Haupt-Spezifikation
│   ├── ADR-canopen-encoder.md     # ADR
│   └── hardware-config.yaml       # Hardware-Infos
│
└── sub-projects/
    ├── hal-layer/
    │   └── input/
    │       └── shared/ → ../../shared/   # Symlink
    │
    └── canopen-stack/
        └── input/
            └── shared/ → ../../shared/   # Symlink
```

---

# Teil 5: MaxVP - Parallele Ausführung

> **Konzept:** DAG-basierte Dependencies für maximale Parallelität
> **Aufwand:** 1-2 Wochen

## 5.1 DAG-Modell

```
                    ┌─────────────────┐
                    │   CONSULTANT    │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │   FEASIBILITY   │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
       ┌────────────┐ ┌────────────┐ ┌────────────┐
       │ HAL-GPIO   │ │ HAL-SPI    │ │ HAL-TIMER  │
       └─────┬──────┘ └─────┬──────┘ └─────┬──────┘
              │              │              │
              └──────────────┼──────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  CANOPEN-STACK  │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
       ┌────────────┐ ┌────────────┐ ┌────────────┐
       │  UNIT-TEST │ │  HIL-TEST  │ │    DOCS    │
       └────────────┘ └────────────┘ └────────────┘
```

## 5.2 phases.yaml mit Dependencies

```yaml
# phases.yaml

project:
  name: canopen-encoder
  type: complex
  parallel: true  # Parallele Ausführung aktiviert

phases:
  - id: consultant
    type: consultant

  - id: feasibility
    type: feasibility
    depends_on: [consultant]

  # Diese drei können parallel laufen!
  - id: hal-gpio
    type: development
    depends_on: [feasibility]

  - id: hal-spi
    type: development
    depends_on: [feasibility]

  - id: hal-timer
    type: development
    depends_on: [feasibility]

  - id: canopen-stack
    type: development
    depends_on: [hal-gpio, hal-spi, hal-timer]  # Wartet auf alle drei

  # Diese drei können wieder parallel laufen!
  - id: unit-test
    type: testing
    depends_on: [canopen-stack]

  - id: hil-test
    type: hardware-test
    depends_on: [canopen-stack]

  - id: docs
    type: documentation
    depends_on: [canopen-stack]
```

## 5.3 Parallel Runner Implementation

```python
class ParallelOrchestratorRunner:
    """Führt Phasen parallel aus wo möglich."""

    async def run(self, project_name: str) -> ProjectStatus:
        phases = self.load_phases(project_name)

        # DAG aufbauen
        dag = self._build_dag(phases)

        # Topologische Sortierung + Parallelisierung
        while not dag.all_complete():
            # Finde alle Phasen ohne offene Dependencies
            ready_phases = dag.get_ready_phases()

            if not ready_phases:
                # Deadlock oder Fehler
                break

            # Parallel ausführen
            tasks = [
                self._run_phase(phase)
                for phase in ready_phases
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Status updaten
            for phase, result in zip(ready_phases, results):
                if isinstance(result, Exception):
                    dag.mark_failed(phase.id, str(result))
                else:
                    dag.mark_complete(phase.id)

        return self._get_final_status(dag)

    def _build_dag(self, phases: list[PhaseConfig]) -> DAG:
        """Baut DAG aus phases.yaml."""
        dag = DAG()

        for phase in phases:
            dag.add_node(phase.id, phase)

            for dep in phase.config.get("depends_on", []):
                dag.add_edge(dep, phase.id)

        return dag
```

## 5.4 Critical Path Berechnung

```python
class DAG:
    def get_critical_path(self) -> list[str]:
        """Berechnet den kritischen Pfad (längster Pfad)."""

        # Topologische Sortierung
        sorted_nodes = self._topological_sort()

        # Längsten Pfad zu jedem Knoten berechnen
        distances = {node: 0 for node in sorted_nodes}
        predecessors = {node: None for node in sorted_nodes}

        for node in sorted_nodes:
            for successor in self.get_successors(node):
                weight = self.nodes[successor].estimated_duration
                if distances[node] + weight > distances[successor]:
                    distances[successor] = distances[node] + weight
                    predecessors[successor] = node

        # Pfad rekonstruieren
        end_node = max(distances, key=distances.get)
        path = []
        current = end_node
        while current:
            path.append(current)
            current = predecessors[current]

        return list(reversed(path))
```

## 5.5 Visualisierung Paralleler Ausführung

```
Timeline:
─────────────────────────────────────────────────────────────────────
T0      T1      T2      T3      T4      T5      T6      T7      T8

[consultant]
        [feasibility      ]
                [hal-gpio ]
                [hal-spi  ]         ← Parallel!
                [hal-timer]
                        [canopen-stack        ]
                                        [unit-test]
                                        [hil-test ]  ← Parallel!
                                        [docs     ]
─────────────────────────────────────────────────────────────────────

Critical Path: consultant → feasibility → hal-gpio → canopen-stack → hil-test
Estimated Duration: T0 → T8
Parallelization Savings: ~30%
```

---

# Teil 6: Roadmap

## 6.1 Implementation Timeline

```
┌─────────────────────────────────────────────────────────────────┐
│                    IMPLEMENTATION ROADMAP                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  PHASE 1: MVP                                     [2 Wochen]    │
│  ─────────────                                                  │
│  ├── OrchestratorRunner                           [3 Tage]     │
│  ├── PhaseExecutor                                [2 Tage]     │
│  ├── DataFlowManager                              [1 Tag]      │
│  ├── StatusTracker                                [1 Tag]      │
│  ├── CLI Integration                              [2 Tage]     │
│  └── Testing & Docs                               [3 Tage]     │
│                                                                 │
│  PHASE 2: Domain Consultants                      [2-3 Wochen] │
│  ────────────────────────                                       │
│  ├── ConsultantMeeting                            [3 Tage]     │
│  ├── Domain-Expert Config                         [2 Tage]     │
│  ├── Parallel Expert Execution                    [2 Tage]     │
│  ├── Synthesis Logic                              [3 Tage]     │
│  └── Testing & Docs                               [2 Tage]     │
│                                                                 │
│  PHASE 3: Hardware-Tool Integration               [2-3 Wochen] │
│  ───────────────────────────────                                │
│  ├── Tool Skill Format                            [2 Tage]     │
│  ├── SSH Executor                                 [3 Tage]     │
│  ├── JTAG Tool                                    [2 Tage]     │
│  ├── Oscilloscope Tool                            [2 Tage]     │
│  ├── HIL Phase Type                               [2 Tage]     │
│  └── Testing & Docs                               [2 Tage]     │
│                                                                 │
│  PHASE 4: Projekt-Hierarchie                      [2 Wochen]   │
│  ───────────────────────────                                    │
│  ├── Sub-Project Support                          [3 Tage]     │
│  ├── Status Aggregation                           [2 Tage]     │
│  ├── Shared Context                               [2 Tage]     │
│  └── Testing & Docs                               [3 Tage]     │
│                                                                 │
│  PHASE 5: Parallele Ausführung                    [1-2 Wochen] │
│  ─────────────────────────────                                  │
│  ├── DAG Builder                                  [2 Tage]     │
│  ├── ParallelRunner                               [3 Tage]     │
│  ├── Critical Path                                [2 Tage]     │
│  └── Testing & Docs                               [2 Tage]     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 6.2 Dependencies zwischen Features

```
                    ┌─────────────────┐
                    │   MVP (Teil 1)  │
                    │   Foundation    │
                    └────────┬────────┘
                             │
           ┌─────────────────┼─────────────────┐
           │                 │                 │
           ▼                 ▼                 ▼
    ┌────────────┐    ┌────────────┐    ┌────────────┐
    │  Domain    │    │  Hardware  │    │  Projekt-  │
    │ Consultants│    │   Tools    │    │ Hierarchie │
    │  (Teil 2)  │    │  (Teil 3)  │    │  (Teil 4)  │
    └────────────┘    └────────────┘    └─────┬──────┘
                                              │
                                              ▼
                                       ┌────────────┐
                                       │  Parallele │
                                       │ Ausführung │
                                       │  (Teil 5)  │
                                       └────────────┘
```

## 6.3 Feature-Matrix

| Feature | MVP | MaxVP | Abhängigkeit |
|---------|-----|-------|--------------|
| Basis-Orchestrator | ✅ | - | - |
| Linearer Datenfluss | ✅ | - | - |
| Status-Tracking | ✅ | - | - |
| CLI & API | ✅ | - | - |
| Quality Gates (fix) | ✅ | - | - |
| Domain Consultants | - | ✅ | MVP |
| Sub-Agenten | - | ✅ | MVP |
| Hardware-Tools | - | ✅ | MVP |
| SSH Executor | - | ✅ | MVP |
| MCP Server (optional) | - | ✅ | Hardware-Tools |
| Sub-Projekte | - | ✅ | MVP |
| Status-Aggregation | - | ✅ | Sub-Projekte |
| DAG Dependencies | - | ✅ | Sub-Projekte |
| Parallele Ausführung | - | ✅ | DAG Dependencies |
| Critical Path | - | ✅ | Parallele Ausführung |

## 6.4 Risiken und Mitigationen

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|-------------------|--------|------------|
| Claude CLI Änderungen | Mittel | Hoch | Abstraktion via PhaseExecutor |
| SSH-Verbindungsprobleme | Mittel | Mittel | Retry + Timeout Handling |
| Parallele Race Conditions | Niedrig | Hoch | Ausführliches Testing |
| Komplexität wächst | Hoch | Mittel | Modulare Architektur |
| Token-Kosten steigen | Hoch | Mittel | Dry-Run, Gate-First |

## 6.5 Empfohlene Reihenfolge

1. **Sofort (Woche 1-2):** MVP implementieren - Basis-Orchestrator mit linearem Workflow
2. **Danach (Woche 3-4):** Domain Consultants - wenn mehr als eine Domain relevant
3. **Bei Bedarf:** Hardware-Tools - wenn Hardware-Projekte anstehen
4. **Später:** Projekt-Hierarchie - wenn Projekte größer werden
5. **Optimierung:** Parallele Ausführung - wenn Geschwindigkeit kritisch wird

---

# Anhang: Vollständiges Beispiel

## Encoder-Firmware Projekt (Complex Type)

```yaml
# projects/canopen-encoder/project.yaml

project:
  name: canopen-encoder
  type: complex
  description: "CAN-Open Drehgeber Firmware für neue Hardware"

config:
  parallel: true
  max_retries: 3
  timeout_per_phase: 1200  # 20 Minuten

sub_projects:
  - id: feasibility
  - id: hal-layer
  - id: canopen-stack
  - id: hil-test
```

```yaml
# projects/canopen-encoder/phases.yaml

phases:
  - id: consultant
    type: consultant
    domain_experts: [encoder, infrastructure]
    output: [ADR, spec.yaml, phases.yaml]

  - id: feasibility
    type: feasibility
    depends_on: [consultant]
    tools: [jtag]
    gate: poc_working

  - id: hal-gpio
    type: development
    depends_on: [feasibility]

  - id: hal-spi
    type: development
    depends_on: [feasibility]

  - id: hal-timer
    type: development
    depends_on: [feasibility]

  - id: canopen-stack
    type: development
    depends_on: [hal-gpio, hal-spi, hal-timer]

  - id: hil-test
    type: hardware-test
    depends_on: [canopen-stack]
    tools: [jtag, oscilloscope, can-interface]
    ssh:
      host: lab-server.local
      user: helix

  - id: integration
    type: integration
    depends_on: [hil-test]
```

```bash
# Projekt erstellen und ausführen
helix project create canopen-encoder --type complex

# Orchestrator startet
helix project run canopen-encoder

# Output:
# [10:00] Starting canopen-encoder (complex)
# [10:01] Phase: consultant - Running Domain Experts Meeting
# [10:05] Phase: consultant - Completed
# [10:06] Phase: feasibility - Running
# [10:30] Phase: feasibility - Completed (POC working)
# [10:31] Starting parallel phases: hal-gpio, hal-spi, hal-timer
# [11:00] Phase: hal-gpio - Completed
# [11:05] Phase: hal-timer - Completed
# [11:10] Phase: hal-spi - Completed
# [11:11] Phase: canopen-stack - Running
# [12:00] Phase: canopen-stack - Completed
# [12:01] Phase: hil-test - Running (SSH: lab-server.local)
# [12:30] Phase: hil-test - Completed (All tests passed)
# [12:31] Phase: integration - Running
# [12:35] Phase: integration - Completed
# ✅ Project canopen-encoder completed successfully!
```

---

*Dokument erstellt vom HELIX Consultant*
*Session: orchestrator-full*
