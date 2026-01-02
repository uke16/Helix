# HELIX Orchestrator Architecture - Complete Design

> MVP + MaxVP: Von Basis bis Vision
>
> Stand: 2025-12-23
> 
> **Erstellt durch:** Best-of-Both-Worlds aus:
> - Claude Opus (701 Zeilen) - kompakt, gute Übersicht
> - Consultant CLI (1445 Zeilen) - detailliert, konkrete Implementation

---

## Übersicht: MVP vs MaxVP

```
┌─────────────────────────────────────────────────────────────────┐
│                         HELIX ORCHESTRATOR                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  MVP (2 Wochen)                    MaxVP (2-3 Monate)           │
│  ─────────────                     ──────────────────           │
│  ✓ Basis-Orchestrator              ○ Domain Consultants         │
│  ✓ Sequentielle Phasen             ○ Hardware-Tool Integration  │
│  ✓ Einfacher Datenfluss            ○ Projekt-Hierarchie         │
│  ✓ Feste Quality Gates             ○ Parallele Ausführung       │
│  ✓ CLI: create/run/status          ○ DAG-basierte Dependencies  │
│  ✓ Status-Tracking                 ○ Dynamic Gate Planning      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---
# TEIL 1: MVP (2 Wochen)

## 1.1 Kern-Architektur

```
┌─────────────────────────────────────────────────────────────┐
│                      ORCHESTRATOR                           │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ PhaseRunner │  │ GateChecker │  │ StatusTracker│         │
│  │             │  │             │  │             │         │
│  │ Spawnt CLI  │  │ Prüft Gates │  │ status.yaml │         │
│  │ Wartet      │  │ Retry       │  │ Pause/Resume│         │
│  │ Kopiert I/O │  │ Escalate    │  │             │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

## 1.2 Projekt-Struktur

```
projects/
└── my-feature/
    ├── project.yaml          # Name, Type, Meta
    ├── phases.yaml           # Phase-Definitionen
    ├── status.yaml           # Orchestrator-Status (generiert)
    │
    └── phases/
        ├── 01-consultant/
        │   ├── CLAUDE.md     # Instruktionen
        │   ├── input/        # Vom Orchestrator befüllt
        │   └── output/       # Von Claude Code CLI
        │
        └── 02-development/
            ├── CLAUDE.md
            ├── input/        # ← Kopiert von 01/output
            └── output/
```

## 1.3 Sequentieller Ablauf

```python
# MVP: Einfache Schleife
async def run(self):
    for phase in self.phases:
        if self.status.is_complete(phase.id):
            continue
        
        await self.prepare_inputs(phase)
        result = await self.run_phase(phase)
        gate_result = await self.check_gates(phase)
        
        if not gate_result.passed:
            if phase.retries < phase.max_retries:
                phase.retries += 1
                continue  # Retry
            else:
                self.status.mark_failed(phase.id)
                return False
        
        self.status.mark_complete(phase.id)
    
    return True
```

## 1.4 Datenfluss (einfach)

```yaml
# phases.yaml
phases:
  - id: development
    input_from:
      consultant: [spec.yaml, ADR-*.md]
```

```python
# Orchestrator kopiert
for source_phase, patterns in phase.input_from.items():
    src_dir = project_dir / "phases" / source_phase / "output"
    dst_dir = project_dir / "phases" / phase.id / "input"
    
    for pattern in patterns:
        for file in src_dir.glob(pattern):
            shutil.copy(file, dst_dir / file.name)
```

## 1.5 Quality Gates (fix)

```yaml
# config/phase-types.yaml
phase_types:
  consultant:
    gates: [adr_valid]
  development:
    gates: [files_exist, syntax_check, tests_pass]
  review:
    gates: [review_approved]
```

## 1.6 CLI

```bash
helix project create my-feature --type simple
helix project run my-feature
helix project run my-feature --resume
helix project status my-feature
```

---

# TEIL 2: MaxVP - Domain Consultants

## 2.1 Konzept: Sub-Agenten

**Aus ADR-005 (existiert schon!):**

```
┌─────────────────────────────────────────────────────────────┐
│                    HAUPT-CONSULTANT                         │
│                                                             │
│  Analysiert Request und entscheidet:                        │
│  - Welche Domain(s) betroffen?                              │
│  - Welche Experten einbinden?                               │
│                                                             │
│         ┌──────────┬──────────┬──────────┐                  │
│         ▼          ▼          ▼          ▼                  │
│    ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐         │
│    │ PDM     │ │ Encoder │ │ Infra   │ │ API     │         │
│    │ Expert  │ │ Expert  │ │ Expert  │ │ Expert  │         │
│    │         │ │         │ │         │ │         │         │
│    │skills/  │ │skills/  │ │skills/  │ │skills/  │         │
│    │pdm/     │ │encoder/ │ │infra/   │ │api/     │         │
│    └─────────┘ └─────────┘ └─────────┘ └─────────┘         │
└─────────────────────────────────────────────────────────────┘
```

## 2.2 Routing-Logik

```yaml
# config/domain-routing.yaml
domains:
  pdm:
    keywords: [stückliste, artikel, bom, produkt, stammdaten]
    skill_path: skills/pdm/
    consultant_prompt: |
      Du bist PDM-Experte. Du verstehst Stücklisten, Artikel, 
      und das Legacy-PDM-System.
      
  encoder:
    keywords: [drehgeber, sensor, canopen, biss, ssi, posital]
    skill_path: skills/encoder/
    consultant_prompt: |
      Du bist Encoder-Experte. Du verstehst Hardware, Firmware,
      und Kommunikationsprotokolle für Drehgeber.
      
  infrastructure:
    keywords: [docker, postgres, deployment, server, ssh]
    skill_path: skills/infrastructure/
    consultant_prompt: |
      Du bist Infrastructure-Experte. Du verstehst Container,
      Datenbanken, und Deployment.
```

## 2.3 Haupt-Consultant Ablauf

```python
# In Consultant-Phase CLAUDE.md
"""
## Schritt 1: Request analysieren

Lies `input/request.md` und identifiziere:
- Betroffene Domain(s)
- Benötigte Expertise

## Schritt 2: Domain-Experten einbinden

Für jede relevante Domain:
1. Lies den Domain-Skill: `skills/{domain}/SKILL.md`
2. Nutze das Domain-Wissen für deine Analyse

## Schritt 3: ADR schreiben

Mit dem kombinierten Wissen:
- Schreibe ADR mit vollständigem Kontext
- Referenziere relevante Domain-Skills
- Setze `domain:` im YAML Header
"""
```

## 2.4 Beispiel: Cross-Domain Request

```
User: "Exportiere PDM-Artikeldaten nach CANopen EDS Format"

Haupt-Consultant:
├── Erkennt: PDM + Encoder betroffen
├── Liest: skills/pdm/SKILL.md (Artikelstruktur)
├── Liest: skills/encoder/canopen/SKILL.md (EDS Format)
├── Kombiniert Wissen
└── Output: ADR mit domain: [pdm, encoder]
```

## 2.5 Implementation (einfach!)

**Das ist kein neuer Code** - nur bessere CLAUDE.md Templates:

```markdown
# Consultant CLAUDE.md Template

## Domain-Analyse

Analysiere den Request und identifiziere relevante Domains:

| Domain | Keywords | Skill-Pfad |
|--------|----------|------------|
| pdm | stückliste, artikel | skills/pdm/ |
| encoder | drehgeber, canopen | skills/encoder/ |
| infrastructure | docker, postgres | skills/infrastructure/ |

## Bei Match: Lies den Skill

Für jede erkannte Domain:
```
Lies: skills/{domain}/SKILL.md
```

## Dann: Schreibe ADR mit Domain-Wissen
```

**Aufwand: 1-2 Tage** (Templates + Routing-Config)

---


### 2.6 Implementation: ConsultantMeeting (aus Consultant-Version)

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
```
# TEIL 3: MaxVP - Hardware-Tool Integration

## 3.1 Kern-Insight: Es ist nur Python + Dokumentation

```
┌─────────────────────────────────────────────────────────────┐
│                    HARDWARE-TOOL PATTERN                    │
│                                                             │
│   Claude.ai ──SSH──► helix-server ──Python──► Hardware      │
│                           │                                 │
│                           │                                 │
│                      ┌────▼────┐                            │
│                      │ pyocd   │ ──► JTAG Debugger          │
│                      │ pyvisa  │ ──► Oscilloscope           │
│                      │ pyserial│ ──► Serial/CAN             │
│                      │ minimalmodbus│ ──► Modbus            │
│                      └─────────┘                            │
│                                                             │
│   Alles was Claude braucht: Dokumentation im Skill-Format   │
└─────────────────────────────────────────────────────────────┘
```

## 3.2 Tool-Skill Format

```
skills/tools/jtag/
├── SKILL.md              # Wie man JTAG nutzt
├── examples/
│   ├── flash_firmware.py
│   ├── read_memory.py
│   └── debug_session.py
├── requirements.txt      # pyocd
└── config/
    └── targets.yaml      # Bekannte MCUs
```

## 3.3 SKILL.md für JTAG

```markdown
# JTAG Debugger Tool

## Setup

```bash
pip install pyocd
```

## Grundlegende Nutzung

### Firmware flashen

```python
from pyocd.core.helpers import ConnectHelper

# Verbindung herstellen
session = ConnectHelper.session_with_chosen_probe(
    target_override='nrf52840'
)

# Firmware flashen
session.target.flash.program('firmware.hex')
session.close()
```

### Memory lesen

```python
# 256 Bytes ab Adresse 0x20000000 lesen
data = session.target.read_memory_block8(0x20000000, 256)
```

### Register lesen

```python
# Program Counter lesen
pc = session.target.read_core_register('pc')
```

## Verfügbare Targets

- nrf52840 (Nordic)
- stm32f4 (STM32F4xx)
- lpc1768 (NXP LPC)

## Fehlerbehandlung

```python
try:
    session = ConnectHelper.session_with_chosen_probe()
except Exception as e:
    print(f"JTAG Verbindung fehlgeschlagen: {e}")
    # Prüfen: Ist Debugger angeschlossen?
    # Prüfen: Ist Target mit Strom versorgt?
```
```

## 3.4 Claude Code CLI nutzt es automatisch

Wenn Claude Code CLI auf dem Server läuft:

```python
# Claude generiert das basierend auf SKILL.md
import pyocd
from pyocd.core.helpers import ConnectHelper

session = ConnectHelper.session_with_chosen_probe(
    target_override='nrf52840'
)

# Test: Memory lesen
data = session.target.read_memory_block8(0x20000000, 16)
print(f"Memory: {data.hex()}")

session.close()
```

## 3.5 HIL Test Phase

```yaml
# phases.yaml
phases:
  - id: hil-test
    type: hardware-test
    tools: [jtag, oscilloscope]
    
    # Orchestrator prüft: Sind Tools verfügbar?
    pre_check:
      - command: "pyocd list"
        expect: "probe"
      - command: "python -c 'import pyvisa'"
        expect_exit: 0
    
    gate: hil_passed
```

**Aufwand: 2-3 Tage** (Skill-Templates + Pre-Check Logic)

---

# TEIL 4: MaxVP - Projekt-Hierarchie

## 4.1 Konzept: Sub-Projekte

```
projects/
└── encoder-firmware-v2/           # Haupt-Projekt
    ├── project.yaml
    ├── phases.yaml
    ├── status.yaml
    │
    ├── phases/
    │   ├── 01-consultant/
    │   └── 02-feasibility/
    │
    └── sub-projects/              # Sub-Projekte
        ├── hal-layer/
        │   ├── project.yaml
        │   ├── phases.yaml
        │   └── phases/
        │
        └── canopen-stack/
            ├── project.yaml
            ├── phases.yaml
            └── phases/
```

## 4.2 Wann Sub-Projekte?

```yaml
# In plan.yaml vom Planning-Agent
decomposed_phases:
  - id: hal-layer
    type: sub-project          # ← Neuer Typ!
    description: "Hardware Abstraction Layer"
    estimated_phases: 3
    
  - id: canopen-stack
    type: sub-project
    depends_on: [hal-layer]
    description: "CANopen Protocol Stack"
    estimated_phases: 4
```

## 4.3 Status-Tracking

```yaml
# Haupt-Projekt status.yaml
project: encoder-firmware-v2
status: in_progress

phases:
  consultant:
    status: complete
  feasibility:
    status: complete

sub_projects:
  hal-layer:
    status: complete
    phases_complete: 3/3
    
  canopen-stack:
    status: in_progress
    phases_complete: 2/4
    current_phase: implementation
```

## 4.4 Shared Context

```yaml
# Sub-Projekt project.yaml
parent: encoder-firmware-v2
inherit_context:
  - ../phases/01-consultant/output/ADR-*.md
  - ../phases/01-consultant/output/spec.yaml
```

**Aufwand: 1 Woche** (Hierarchie-Management + Status-Aggregation)

---

# TEIL 5: MaxVP - Parallele Ausführung

## 5.1 DAG-basierte Dependencies

```yaml
# phases.yaml mit parallelen Phasen
phases:
  - id: consultant
    type: consultant
    
  - id: dev-frontend
    type: development
    depends_on: [consultant]
    
  - id: dev-backend
    type: development
    depends_on: [consultant]
    # Kann parallel zu dev-frontend!
    
  - id: integration
    type: integration
    depends_on: [dev-frontend, dev-backend]
    # Wartet auf beide
```

## 5.2 Execution Graph

```
         consultant
             │
      ┌──────┴──────┐
      ▼             ▼
 dev-frontend   dev-backend    ← Parallel
      │             │
      └──────┬──────┘
             ▼
        integration
```

## 5.3 Parallel Executor

```python
async def run_parallel(self):
    """DAG-basierte Ausführung."""
    
    completed = set()
    running = {}
    
    while not self.all_complete():
        # Finde ausführbare Phasen (alle deps erfüllt)
        ready = [
            p for p in self.phases
            if p.id not in completed
            and p.id not in running
            and all(d in completed for d in p.depends_on)
        ]
        
        # Starte alle ready Phasen parallel
        for phase in ready:
            task = asyncio.create_task(self.run_phase(phase))
            running[phase.id] = task
        
        # Warte auf erste Completion
        done, _ = await asyncio.wait(
            running.values(),
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # Verarbeite completions
        for task in done:
            phase_id = self.get_phase_id(task)
            result = task.result()
            
            if result.success:
                completed.add(phase_id)
            else:
                # Handle failure
                ...
            
            del running[phase_id]
```

## 5.4 Critical Path

```python
def calculate_critical_path(phases):
    """Berechnet längsten Pfad durch DAG."""
    
    # Topologische Sortierung + Longest Path
    durations = {p.id: p.estimated_duration for p in phases}
    
    earliest_finish = {}
    for phase in topological_sort(phases):
        deps_finish = max(
            (earliest_finish.get(d, 0) for d in phase.depends_on),
            default=0
        )
        earliest_finish[phase.id] = deps_finish + durations[phase.id]
    
    return max(earliest_finish.values())
```

**Aufwand: 1 Woche** (Parallel Execution + Race Condition Handling)

---

# TEIL 6: Roadmap

## Phase 1: MVP (Wochen 1-2)

```
Woche 1:
├── Orchestrator Core (runner.py, phase.py, status.py)
├── CLI Commands (create, run, status)
└── Integration mit existierenden Gates

Woche 2:
├── API Endpoints
├── Phase-Type Defaults (phase-types.yaml)
├── Tests + Dokumentation
└── Test mit echtem Projekt
```

**Deliverable:** `helix project run` funktioniert für simple Projekte

## Phase 2: Domain Consultants (Woche 3)

```
├── Domain-Routing Config (domain-routing.yaml)
├── Consultant CLAUDE.md Template erweitern
├── skills/pdm/ dokumentieren
├── skills/encoder/ Grundstruktur
└── Test: Cross-Domain ADR
```

**Deliverable:** Consultant nutzt automatisch Domain-Skills

## Phase 3: Hardware-Tools (Wochen 4-5)

```
Woche 4:
├── Tool-Skill Format definieren
├── skills/tools/jtag/ erstellen
├── Pre-Check Logic im Orchestrator
└── hardware-test Phase-Type

Woche 5:
├── skills/tools/oscilloscope/
├── skills/tools/can-interface/
├── HIL Test Gate
└── Test mit echter Hardware
```

**Deliverable:** HIL Tests laufen automatisch

## Phase 4: Projekt-Hierarchie (Woche 6)

```
├── Sub-Projekt Erstellung
├── Status-Aggregation
├── Shared Context (inherit_context)
└── Test: Großes Projekt mit Sub-Projekten
```

**Deliverable:** Große Projekte können sich selbst zerlegen

## Phase 5: Parallele Ausführung (Wochen 7-8)

```
Woche 7:
├── DAG Parser
├── Parallel Executor
├── Race Condition Handling
└── Tests

Woche 8:
├── Critical Path Berechnung
├── Resource Limits (max parallel)
├── Monitoring Dashboard
└── Performance Tests
```

**Deliverable:** Phasen laufen parallel wo möglich

---

## Zusammenfassung: MVP vs MaxVP

| Feature | MVP | MaxVP | Aufwand |
|---------|-----|-------|---------|
| Basis-Orchestrator | ✅ | ✅ | 2 Wochen |
| Sequentielle Phasen | ✅ | ✅ | - |
| Status-Tracking | ✅ | ✅ | - |
| CLI + API | ✅ | ✅ | - |
| Domain Consultants | ❌ | ✅ | 1 Woche |
| Hardware-Tools | ❌ | ✅ | 2 Wochen |
| Projekt-Hierarchie | ❌ | ✅ | 1 Woche |
| Parallele Ausführung | ❌ | ✅ | 2 Wochen |
| **Gesamt** | **2 Wochen** | **8 Wochen** | |

---

## Abhängigkeiten

```
MVP ──────────────────┐
                      │
Domain Consultants ───┼──► Kann parallel
                      │
Hardware-Tools ───────┼──► Kann parallel
                      │
                      ▼
Projekt-Hierarchie ───► Braucht MVP
                      │
                      ▼
Parallele Ausführung ─► Braucht MVP + Hierarchie
```

---

# Anhang: Vollständiges Beispiel (aus Consultant-Version)

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

