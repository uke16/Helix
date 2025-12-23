# HELIX v4 Vision

> Die langfristige Vision für HELIX und das Delta zum aktuellen Stand
>
> Stand: 2025-12-23
> Autor: Uwe (via Claude Opus Session)

---

## Evolution: Was ich gelernt habe

### v1: Multi-Agent Chaos
**Ansatz:** Claude baut Multi-Agent System mit Meetings und Diskussionen
**Problem:** Nach 7 Tagen wusste niemand mehr was gebaut wurde
**Lerning:** Context Loss über Sessions ist tödlich

### v2: Strikte Skripte
**Ansatz:** HELIX ist skriptbar von außen, keine Intelligenz
**Problem:** Zu rigide, keine Flexibilität
**Learning:** Single Source of Truth ist essentiell

### v3: Hybrid mit eigenen Agenten
**Ansatz:** Definierte Prozesse + freie Agenten mit Tool-Calls
**Was gut war:**
- Perfekte Dokumentation beim Erstellen
- Consultant funktionierte hervorragend
- Context is King → perfekter Context pro Domäne

**Was schlecht war:**
- Developer/Reviewer Agenten "dümmlich"
- 10x hintereinander `think` ohne Auswertung
- Eigene Agent-Harness ist Wartungsaufwand

**Learning:** 
- KI lernt besser an Beispielen als wenn sie selbst überlegt
- Patterns wie Decomposition und Planning sind wichtig
- Agent-Harness selbst bauen lohnt sich nicht

### v4: Claude Code CLI als Agent-Ersatz
**Ansatz:** 
- Agenten = Claude Code CLI Instanzen
- Kommunikation via Dateien und strukturierte Outputs
- Best of both worlds: Schlaue Agenten + strikter Rahmen
- OpenRouter für andere Modelle möglich

**Kernidee:**
- Nicht die Agenten "schlau machen"
- Sondern den Rahmen perfekt machen
- Claude Code CLI ist maintained und wird besser

---

## Die Vision: Dynamische Projekt-Orchestrierung

### Kern-Konzept

```
┌─────────────────────────────────────────────────────────────┐
│                         USER                                │
│  "Baue CAN-Open Drehgeber Firmware für neue Hardware"       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      CONSULTANT                             │
│  - Versteht Domain (Drehgeber, CAN, Hardware)               │
│  - Klärt Anforderungen                                      │
│  - Bewertet Komplexität                                     │
│  - Empfiehlt Projekt-Typ                                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    DECOMPOSE TASK                           │
│  Komplexität: HOCH                                          │
│  → Empfehlung: Feasibility zuerst                           │
│                                                             │
│  phases.yaml (dynamisch generiert):                         │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ project: canopen-encoder-v2                         │    │
│  │ type: hardware-firmware                             │    │
│  │                                                     │    │
│  │ phases:                                             │    │
│  │   - id: feasibility                                 │    │
│  │     type: feasibility                               │    │
│  │     goals: [hardware-check, sensor-test]            │    │
│  │     tools: [jtag, oscilloscope]                     │    │
│  │     gate: poc_working                               │    │
│  │                                                     │    │
│  │   - id: planning                                    │    │
│  │     type: planning                                  │    │
│  │     depends_on: [feasibility]                       │    │
│  │     decompose: true  # Kann Sub-Phasen erzeugen     │    │
│  │                                                     │    │
│  │   - id: implementation                              │    │
│  │     type: development                               │    │
│  │     depends_on: [planning]                          │    │
│  │     includes: [review, documentation]               │    │
│  │                                                     │    │
│  │   - id: hil-test                                    │    │
│  │     type: hardware-test                             │    │
│  │     tools: [jtag, can-interface, motor]             │    │
│  │     gate: hil_passed                                │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      ORCHESTRATOR                           │
│  - Führt Phasen aus (Claude Code CLI)                       │
│  - Prüft Quality Gates                                      │
│  - Handhabt Failures (Retry, Escalate)                      │
│  - Kann neue Phasen dynamisch hinzufügen                    │
│  - Kommunikation via Dateien                                │
└─────────────────────────────────────────────────────────────┘
```

### Projekt-Typen

```yaml
project_types:

  # Schnelles Ausprobieren
  feasibility:
    phases: [consultant, poc]
    gates: [poc_working]
    includes_review: false
    includes_docs: minimal
    
  # Standard Software Feature  
  software-feature:
    phases: [consultant, planning, development, review, integration]
    gates: [adr_valid, tests_pass, review_approved]
    includes_review: true
    includes_docs: true
    
  # Hardware-Firmware Projekt
  hardware-firmware:
    phases: [consultant, feasibility, planning, development, hil-test, integration]
    gates: [adr_valid, tests_pass, hil_passed]
    tools_required: [jtag, oscilloscope]
    includes_review: true
    includes_docs: true
    
  # Nur Dokumentation
  documentation:
    phases: [consultant, writing, review]
    gates: [docs_complete]
    includes_review: true
```

### Domain Consultants

```
┌─────────────────────────────────────────────────────────────┐
│                    DOMAIN KNOWLEDGE                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  skills/encoder/                                            │
│  ├── SKILL.md           # Übersicht                         │
│  ├── hardware/                                              │
│  │   ├── pcb-blocks.md  # Platine, Funktionsblöcke          │
│  │   ├── sensors.md     # Sensor-Typen, Interfaces          │
│  │   └── interfaces.md  # CAN, SSI, BiSS, etc.              │
│  ├── firmware/                                              │
│  │   ├── architecture.md # Init, Config, Main Loop          │
│  │   ├── canopen.md     # CANopen Stack, EDS                │
│  │   └── examples/      # Referenz-Implementierungen        │
│  └── tools/                                                 │
│      ├── jtag.md        # JTAG Debugger Nutzung             │
│      └── hil.md         # Hardware-in-the-Loop Setup        │
│                                                             │
│  → Consultant liest relevante Skills                        │
│  → Versteht Hardware + Firmware + Tools                     │
│  → Kann intelligente Fragen stellen                         │
│  → Kann realistische Phasen planen                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Hardware-Tools als Claude Code Extensions

```yaml
# tools/jtag/TOOL.md
name: JTAG Debugger
type: hardware-tool
python_driver: pyocd  # oder: jlink, openocd

capabilities:
  - flash_firmware
  - read_memory
  - set_breakpoint
  - read_registers
  - step_execution

claude_code_integration:
  # Claude Code CLI kann diese Tools nutzen
  mcp_server: tools/jtag/mcp_server.py
  
  # Oder: Bash Commands
  commands:
    flash: "pyocd flash --target nrf52 {firmware}"
    reset: "pyocd reset"
    
# tools/oscilloscope/TOOL.md
name: Oscilloscope
type: hardware-tool
python_driver: pyvisa

capabilities:
  - capture_waveform
  - measure_frequency
  - measure_amplitude
  - trigger_on_edge

claude_code_integration:
  mcp_server: tools/oscilloscope/mcp_server.py
```

### Hierarchische Projekt-Zerlegung

```
User Request: "Baue CAN-Open Drehgeber"
         │
         ▼
┌─────────────────────────────────────────┐
│ PROJECT: canopen-encoder                │
│ Status: planning                        │
│                                         │
│ Sub-Projects:                           │
│ ├── feasibility/  [✅ complete]         │
│ │   └── poc-sensor-reading              │
│ │                                       │
│ ├── planning/     [🔄 in-progress]      │
│ │   ├── planning-hardware  [✅]         │
│ │   ├── planning-firmware  [🔄]         │
│ │   └── planning-test      [⏳]         │
│ │                                       │
│ ├── development/  [⏳ waiting]          │
│ │   ├── dev-hal-layer                   │
│ │   ├── dev-canopen-stack               │
│ │   ├── dev-application                 │
│ │   └── dev-bootloader                  │
│ │                                       │
│ └── hil-test/     [⏳ waiting]          │
│     ├── test-basic-function             │
│     ├── test-canopen-conformance        │
│     └── test-endurance                  │
└─────────────────────────────────────────┘
```

---

## Delta: Was fehlt zum Ziel

### Aktueller Stand (v4 heute)

```
✅ Implementiert:
├── ADR System (Templates, Validation, Approval-Code)
├── Quality Gates (adr_valid, files_exist, syntax_check, tests_pass)
├── Doc Generation (YAML → Jinja2 → Markdown)
├── Pre-Commit Enforcement
└── Consultant Workflow (in CLAUDE.md)

⚠️ Teilweise:
├── Approval System (Code existiert, nie aufgerufen)
├── Rejection Handling (Code existiert, nicht integriert)
└── Gates (Bugs in Regex/Parser)

❌ Fehlt komplett:
├── Phase Orchestrator
├── Dynamic Phase Planning (decompose_task)
├── Projekt-Hierarchie (Sub-Projekte)
├── Hardware-Tool Integration
├── HELIX CLI
└── Projekt-Templates
```

### Roadmap zum Ziel

```
PHASE 1: Foundation (2 Wochen)
├── Bug Fixes (BACKLOG Sprint 1)
├── Phase Orchestrator MVP
│   ├── Lädt phases.yaml
│   ├── Spawnt Claude Code CLI
│   ├── Prüft Gates
│   └── Einfaches Retry
└── HELIX CLI (project create/run/status)

PHASE 2: Dynamic Planning (2-3 Wochen)
├── decompose_task Phase-Type
├── Planning Phase kann neue Phasen erzeugen
├── Projekt-Hierarchie (Sub-Projekte)
└── Projekt-Templates (feasibility, software, hardware)

PHASE 3: Hardware Integration (2-3 Wochen)
├── Tool-Definition Format (TOOL.md)
├── MCP Server für Hardware-Tools
├── HIL Test Phase-Type
└── Beispiel: JTAG + Oscilloscope

PHASE 4: Domain Consultants (ongoing)
├── skills/encoder/ ausbauen
├── skills/pdm/ vervollständigen
├── Referenz-Projekte als Beispiele
└── Domain-spezifische Quality Gates
```

---

## Architektur-Analyse: Was muss geändert werden?

### 1. phases.yaml Format erweitern

**Aktuell:**
```yaml
phases:
  - id: consultant
    type: consultant
    output: [output/spec.yaml]
```

**Benötigt:**
```yaml
project:
  name: canopen-encoder
  type: hardware-firmware
  
phases:
  - id: feasibility
    type: feasibility
    can_spawn_subproject: true  # Kann Sub-Projekt erzeugen
    tools: [jtag]
    gate: poc_working
    on_failure:
      action: escalate
      to: human
      
  - id: planning
    type: planning
    depends_on: [feasibility]
    decompose: true  # Kann weitere Phasen hinzufügen
    max_sub_phases: 5
    
  - id: development
    type: development
    depends_on: [planning]
    includes: [review, documentation]  # Automatisch angehängt
    parallel: false  # Sequentiell
    
  - id: hil-test
    type: hardware-test
    depends_on: [development]
    tools: [jtag, oscilloscope, can-interface]
    gate: hil_passed
    retry:
      max: 3
      with_feedback: true
```

### 2. Orchestrator-Architektur

**Nicht empfohlen:** Monolithischer Orchestrator
```python
# ❌ Zu komplex, schwer zu debuggen
class MegaOrchestrator:
    def run_everything(self):
        # 500 Zeilen verschachtelte Logik
```

**Empfohlen:** Event-basierte Pipeline
```python
# ✅ Modulare Architektur
class PhaseRunner:
    """Führt einzelne Phase aus"""
    async def run(self, phase: Phase) -> PhaseResult

class GateChecker:
    """Prüft Quality Gates"""
    async def check(self, phase: Phase, result: PhaseResult) -> GateResult

class Decomposer:
    """Zerlegt komplexe Tasks"""
    async def decompose(self, task: Task) -> list[Phase]

class Orchestrator:
    """Koordiniert alles"""
    def __init__(self):
        self.runner = PhaseRunner()
        self.checker = GateChecker()
        self.decomposer = Decomposer()
    
    async def run_project(self, project: Project):
        phases = project.phases
        
        while phases:
            phase = phases.pop(0)
            
            # Decompose wenn nötig
            if phase.decompose:
                new_phases = await self.decomposer.decompose(phase)
                phases = new_phases + phases
                continue
            
            # Phase ausführen
            result = await self.runner.run(phase)
            
            # Gate prüfen
            gate_result = await self.checker.check(phase, result)
            
            if not gate_result.passed:
                action = self.handle_failure(phase, gate_result)
                if action == "retry":
                    phases.insert(0, phase)
                elif action == "abort":
                    break
```

### 3. CLI-to-CLI Kommunikation

**Aktuelles Pattern (gut, beibehalten):**
```
projects/
└── my-feature/
    ├── CLAUDE.md          # Instruktionen für diese Phase
    ├── phases.yaml        # Was soll passieren
    ├── input/             # Was reinkommt
    │   ├── request.md
    │   └── context/
    └── output/            # Was rauskommt
        ├── ADR-001.md
        └── spec.yaml
```

**Erweiterung für Orchestrator:**
```
projects/
└── my-feature/
    ├── project.yaml       # Projekt-Metadaten
    ├── phases.yaml        # Phasen-Definition
    │
    ├── phases/
    │   ├── 01-consultant/
    │   │   ├── CLAUDE.md
    │   │   ├── input/
    │   │   ├── output/
    │   │   └── result.yaml  # ← Orchestrator schreibt Status
    │   │
    │   ├── 02-development/
    │   │   ├── CLAUDE.md
    │   │   ├── input/       # ← Orchestrator kopiert von 01/output
    │   │   └── output/
    │   │
    │   └── 03-review/
    │
    └── status.yaml        # Projekt-Gesamtstatus
```

### 4. Was an HELIX schlecht ist / geändert werden muss

| Problem | Aktuell | Änderung |
|---------|---------|----------|
| **Kein Orchestrator** | Ich war der Orchestrator | `src/helix/orchestrator/` |
| **phases.yaml zu simpel** | Nur lineare Phasen | Dependencies, Decompose, Parallel |
| **Keine Hierarchie** | Flache Projekte | Sub-Projekte möglich |
| **Hardware-Tools** | Nicht vorgesehen | Tool-Definition + MCP |
| **Consultant zu generisch** | Ein Consultant für alles | Domain-spezifische Consultants |
| **Gates hardcoded** | Python-Code | Gate-Definitionen in YAML |

### 5. Was an HELIX gut ist / beibehalten

| Aspekt | Warum gut |
|--------|-----------|
| **CLI-to-CLI via Dateien** | Einfach, debugbar, versionierbar |
| **CLAUDE.md pro Phase** | Klarer Context |
| **YAML für Konfiguration** | Lesbar, erweiterbar |
| **ADR-System** | Entscheidungen dokumentiert |
| **Quality Gates** | Qualitätssicherung |
| **Generated Docs** | Single Source of Truth |

---

## Realistische Einschätzung

### Was heute schon funktioniert

1. **Consultant → ADR** funktioniert gut
2. **Quality Gates** funktionieren (mit Bugs)
3. **Generated Docs** funktioniert
4. **Claude Code CLI als Agent** funktioniert

### Was 2-4 Wochen Arbeit braucht

1. **Phase Orchestrator MVP**
2. **Bug Fixes**
3. **HELIX CLI**

### Was 2-3 Monate braucht

1. **Dynamic Decomposition**
2. **Hardware-Tool Integration**
3. **Domain Consultants ausbauen**
4. **Projekt-Hierarchie**

### Was von KI-Modell-Verbesserungen abhängt

1. **Komplexe Multi-Step Reasoning**
2. **Lange Projekte ohne Context Loss**
3. **Hardware-Debugging (Oszilloskop-Bilder verstehen)**

---

## Konkrete nächste Schritte

### Diese Woche

1. **BACKLOG Sprint 1** - Bugs fixen
2. **ADR-017: Phase Orchestrator** - Design entscheiden

### Nächste 2 Wochen

1. **Orchestrator MVP implementieren**
2. **HELIX CLI (project create/run)**
3. **Ein echtes Projekt durchführen**

### Danach

1. **Decompose Phase**
2. **Hardware-Tool PoC (JTAG)**
3. **Domain Consultant (Encoder)**

---

## Offene Architektur-Fragen

1. **Wo läuft Orchestrator?**
   - Als Service (immer an)?
   - Als CLI (on-demand)?
   - Als Background Worker?

2. **Wie granular sind Phasen?**
   - Grob: consultant → development → review
   - Fein: consultant → adr-draft → adr-review → adr-approve → ...

3. **Wie handhabt man lange Projekte?**
   - State in Dateien (project.yaml, status.yaml)
   - Kann jederzeit pausieren und fortsetzen
   - Oder: Alles in einem Durchlauf?

4. **Wieviel Parallelität?**
   - Sequentiell (einfach)
   - Parallel wo möglich (schneller)
   - DAG mit Dependencies (komplex)

