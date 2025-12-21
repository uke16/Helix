# ADR-004: Escalation Meeting System

**Status:** Akzeptiert  
**Datum:** 2025-12-21  
**Bezug:** ADR-000, ADR-002

---

## Kontext

Wenn ein Quality Gate mehrfach fehlschlägt, brauchen wir einen strukturierten 
Eskalationsprozess. Der Consultant soll autonom eingreifen können bevor 
ein Mensch involviert wird.

---

## Entscheidung

### 2-Stufiges Escalation System

```
┌─────────────────────────────────────────────────────────────────┐
│                   QUALITY GATE FAILURE                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   Versuch 1-3: Automatischer Retry                              │
│   ─────────────────────────────────                             │
│   • Feedback aus Gate-Failure in CLAUDE.md                      │
│   • Gleiche Konfiguration                                       │
│                                                                  │
│   Nach 3x Fail:                                                 │
│   ▼                                                             │
├─────────────────────────────────────────────────────────────────┤
│   ESCALATION STUFE 1: Consultant-Autonomie (KEIN HIL)           │
│   ───────────────────────────────────────────────────           │
│   Consultant analysiert und kann:                               │
│   • Anderes LLM-Model wählen                                    │
│   • Plan reverten (z.B. Task 10 → Task 5)                       │
│   • Anweisungen/Hints geben                                     │
│   • Spec präzisieren                                            │
│   • Zusätzliche Skills aktivieren                               │
│                                                                  │
│   Dann: Retry mit neuer Konfiguration (1-3 Versuche)            │
│                                                                  │
│   Wenn wieder 3x Fail:                                          │
│   ▼                                                             │
├─────────────────────────────────────────────────────────────────┤
│   ESCALATION STUFE 2: Human-in-the-Loop (HIL)                   │
│   ─────────────────────────────────────────────                 │
│   User wird einbezogen:                                         │
│   • Consultant präsentiert Analyse                              │
│   • Optionen werden vorgeschlagen                               │
│   • User entscheidet                                            │
│   • Ggf. manuelle Intervention                                  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Ablauf-Diagramm

```
Phase N (z.B. Developer)
        │
        ▼
   ┌─────────┐
   │Run Phase│
   └────┬────┘
        │
        ▼
   ┌─────────────┐    PASS
   │Quality Gate │──────────────────────▶ Nächste Phase
   └──────┬──────┘
          │ FAIL
          ▼
   ┌──────────────┐
   │ Retry < 3?   │──YES──▶ Feedback schreiben → Run Phase
   └──────┬───────┘
          │ NO (3x failed)
          ▼
   ┌──────────────────────────────────────┐
   │ ESCALATION STUFE 1                   │
   │ (Consultant-Autonomie, kein HIL)     │
   │                                      │
   │ Consultant analysiert:               │
   │ • Warum ist es fehlgeschlagen?       │
   │ • Welches Model wäre besser?         │
   │ • Muss Plan revidiert werden?        │
   │                                      │
   │ Consultant entscheidet:              │
   │ • model_switch: "gpt-4o" → "claude"  │
   │ • revert_to_task: 5                  │
   │ • additional_hints: [...]            │
   │ • spec_updates: {...}                │
   └──────────────┬───────────────────────┘
                  │
                  ▼
           ┌──────────────┐
           │ Retry 1-3    │
           │ (neue Config)│
           └──────┬───────┘
                  │
                  ▼
           ┌─────────────┐    PASS
           │Quality Gate │──────────────────────▶ Nächste Phase
           └──────┬──────┘
                  │ FAIL (wieder 3x)
                  ▼
   ┌──────────────────────────────────────┐
   │ ESCALATION STUFE 2                   │
   │ (Human-in-the-Loop)                  │
   │                                      │
   │ User erhält:                         │
   │ • Vollständige Analyse               │
   │ • Bisherige Versuche                 │
   │ • Consultant-Empfehlungen            │
   │ • Optionen zur Entscheidung          │
   │                                      │
   │ User entscheidet:                    │
   │ • Weitermachen mit Option X          │
   │ • Manuell eingreifen                 │
   │ • Projekt abbrechen                  │
   └──────────────────────────────────────┘
```

### Stufe 1: Consultant Decision Format

```json
// escalation/stufe-1/consultant-decision.json
{
  "timestamp": "2025-12-21T15:30:00Z",
  "analysis": {
    "failure_summary": "Developer konnte CSV-Export nicht korrekt implementieren",
    "root_cause": "Model hat pandas nicht richtig genutzt, zu komplexer Ansatz",
    "attempts_analyzed": 3
  },
  
  "decision": {
    "action": "retry_with_changes",
    
    "model_switch": {
      "from": "openai/gpt-4o",
      "to": "anthropic/claude-sonnet-4",
      "reasoning": "Claude ist besser für Python/Pandas Code"
    },
    
    "plan_revert": {
      "enabled": true,
      "revert_to_task": 5,
      "current_task": 10,
      "reasoning": "Ab Task 5 war der Ansatz falsch, muss neu gemacht werden"
    },
    
    "additional_hints": [
      "Nutze pandas.DataFrame.to_csv() direkt",
      "Keine eigene CSV-Serialisierung implementieren",
      "Encoding muss UTF-8 mit BOM sein für Excel"
    ],
    
    "spec_updates": {
      "implementation.acceptance_criteria": [
        "CSV muss mit Excel öffenbar sein (UTF-8 BOM)"
      ]
    },
    
    "additional_skills": [
      "python-pandas",
      "csv-excel-compat"
    ]
  },
  
  "expected_outcome": "Mit Claude und dem vereinfachten Ansatz sollte es funktionieren",
  "confidence": 0.8
}
```

### Stufe 2: HIL Request Format

```json
// escalation/stufe-2/hil-request.json
{
  "timestamp": "2025-12-21T16:00:00Z",
  "project_id": "bom-export-csv",
  "phase": "02-developer",
  
  "summary": {
    "total_attempts": 6,
    "stufe_1_interventions": 1,
    "models_tried": ["openai/gpt-4o", "anthropic/claude-sonnet-4"],
    "time_spent_minutes": 45
  },
  
  "consultant_analysis": {
    "problem": "Beide Models scheitern an der Revision-History Logik",
    "suspected_cause": "Die PDM-Datenstruktur ist zu komplex für die aktuelle Spec",
    "learning": "Revision-History braucht eigene Phase oder manuellen Code"
  },
  
  "options": [
    {
      "id": "A",
      "description": "Spec aufteilen: Erst BOM ohne Revision, dann Revision als zweites Feature",
      "effort": "medium",
      "consultant_recommendation": true
    },
    {
      "id": "B",
      "description": "Manuellen Beispiel-Code für Revision-Logik bereitstellen",
      "effort": "high (User muss Code schreiben)"
    },
    {
      "id": "C",
      "description": "Feature vereinfachen: Nur aktuelle Revision exportieren",
      "effort": "low"
    },
    {
      "id": "D",
      "description": "Projekt abbrechen",
      "effort": "none"
    }
  ],
  
  "question_for_user": "Wie sollen wir weitermachen?",
  
  "attachments": {
    "full_logs": "escalation/stufe-2/logs/",
    "code_attempts": "escalation/stufe-2/attempts/",
    "consultant_transcript": "escalation/stufe-2/consultant-analysis.md"
  }
}
```

### Stufe 2: User Decision Format

```json
// escalation/stufe-2/user-decision.json
{
  "timestamp": "2025-12-21T16:15:00Z",
  "chosen_option": "A",
  "user_comment": "Macht Sinn, Revision als separates Feature",
  
  "additional_input": {
    "spec_override": null,
    "manual_code": null,
    "priority_change": "Revision-History wird P2"
  }
}
```

### Verzeichnis-Struktur bei Escalation

```
phases/02-developer/
├── CLAUDE.md
├── src/                      # Arbeitsverzeichnis
├── logs/
│   ├── attempt-1/
│   ├── attempt-2/
│   └── attempt-3/
│
├── escalation/
│   ├── stufe-1/
│   │   ├── trigger.json           # Warum Stufe 1?
│   │   ├── consultant-decision.json
│   │   ├── updated-config.yaml    # Neue Phase-Config
│   │   └── retry-attempts/
│   │       ├── attempt-4/
│   │       ├── attempt-5/
│   │       └── attempt-6/
│   │
│   └── stufe-2/
│       ├── trigger.json           # Warum Stufe 2?
│       ├── hil-request.json       # An User
│       ├── user-decision.json     # Von User
│       ├── resolution.json        # Finale Entscheidung
│       └── attachments/
│           ├── all-attempts.zip
│           └── consultant-analysis.md
│
└── output/                   # Finales Ergebnis (nach Resolution)
```

### Orchestrator Implementation

```python
# escalation.py

from enum import Enum
from dataclasses import dataclass

class EscalationLevel(Enum):
    RETRY = "retry"
    STUFE_1 = "consultant_autonomous"
    STUFE_2 = "human_in_loop"

@dataclass
class EscalationState:
    level: EscalationLevel
    attempts_at_level: int
    total_attempts: int
    models_tried: list[str]
    consultant_interventions: int

async def handle_gate_failure(
    phase_dir: Path,
    gate_result: GateResult,
    state: EscalationState
) -> EscalationAction:
    """Entscheidet über nächste Escalation-Aktion."""
    
    state.total_attempts += 1
    state.attempts_at_level += 1
    
    # Noch im normalen Retry?
    if state.level == EscalationLevel.RETRY:
        if state.attempts_at_level < 3:
            return EscalationAction(
                action="retry",
                feedback=gate_result.to_feedback()
            )
        else:
            # → Stufe 1
            state.level = EscalationLevel.STUFE_1
            state.attempts_at_level = 0
            return await trigger_stufe_1(phase_dir, gate_result, state)
    
    # In Stufe 1?
    elif state.level == EscalationLevel.STUFE_1:
        if state.attempts_at_level < 3:
            return EscalationAction(
                action="retry",
                feedback=gate_result.to_feedback()
            )
        else:
            # → Stufe 2 (HIL)
            state.level = EscalationLevel.STUFE_2
            return await trigger_stufe_2(phase_dir, gate_result, state)
    
    # In Stufe 2 - User muss entscheiden
    else:
        return await wait_for_user_decision(phase_dir)


async def trigger_stufe_1(
    phase_dir: Path,
    gate_result: GateResult,
    state: EscalationState
) -> EscalationAction:
    """Startet Consultant-autonome Escalation."""
    
    escalation_dir = phase_dir / "escalation" / "stufe-1"
    escalation_dir.mkdir(parents=True, exist_ok=True)
    
    # Consultant analysieren lassen
    consultant_decision = await run_consultant_analysis(
        phase_dir=phase_dir,
        gate_failures=collect_all_failures(phase_dir),
        state=state
    )
    
    # Decision speichern
    (escalation_dir / "consultant-decision.json").write_text(
        json.dumps(consultant_decision, indent=2)
    )
    
    # Neue Config basierend auf Consultant-Decision
    new_config = apply_consultant_decision(
        original_config=load_phase_config(phase_dir),
        decision=consultant_decision
    )
    
    # Model Switch?
    if consultant_decision.get("decision", {}).get("model_switch"):
        switch = consultant_decision["decision"]["model_switch"]
        new_config["model"] = switch["to"]
        state.models_tried.append(switch["to"])
    
    # Plan Revert?
    if consultant_decision.get("decision", {}).get("plan_revert", {}).get("enabled"):
        revert = consultant_decision["decision"]["plan_revert"]
        new_config["revert_to_task"] = revert["revert_to_task"]
    
    # Hints in CLAUDE.md einbauen
    if consultant_decision.get("decision", {}).get("additional_hints"):
        update_claude_md_with_hints(
            phase_dir,
            consultant_decision["decision"]["additional_hints"]
        )
    
    # Neue Config speichern
    (escalation_dir / "updated-config.yaml").write_text(
        yaml.dump(new_config)
    )
    
    state.consultant_interventions += 1
    
    return EscalationAction(
        action="retry_with_new_config",
        config=new_config
    )


async def trigger_stufe_2(
    phase_dir: Path,
    gate_result: GateResult,
    state: EscalationState
) -> EscalationAction:
    """Startet Human-in-the-Loop Escalation."""
    
    escalation_dir = phase_dir / "escalation" / "stufe-2"
    escalation_dir.mkdir(parents=True, exist_ok=True)
    
    # HIL Request erstellen
    hil_request = create_hil_request(
        phase_dir=phase_dir,
        state=state,
        all_failures=collect_all_failures(phase_dir)
    )
    
    (escalation_dir / "hil-request.json").write_text(
        json.dumps(hil_request, indent=2)
    )
    
    # User benachrichtigen (via CLI, WebUI, etc.)
    notify_user_hil_required(hil_request)
    
    return EscalationAction(
        action="wait_for_user",
        hil_request=hil_request
    )
```

---

## Konsequenzen

### Positiv
- Consultant kann autonom viele Probleme lösen
- User wird nur bei echten Blocker involviert
- Strukturierte Entscheidungsfindung
- Volle Transparenz über alle Versuche

### Negativ
- Komplexere Logik
- Mehr Dateien/State zu verwalten
- Längere Durchlaufzeit bei Problemen

---

## Referenzen

- ADR-000: Vision & Architecture
- ADR-002: Quality Gate System

