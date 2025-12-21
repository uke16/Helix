# HELIX v4 - Architektur-Entscheidungen

> Basierend auf Diskussion vom 2025-12-21

---

## 1. Consultant Topologie & Agentic Meetings

### Die Frage
Wie spawnt der Consultant Domain-Subagents? Wie funktioniert ein Agentic Meeting?

### Die Entscheidung

```
┌─────────────────────────────────────────────────────────────────┐
│                    CONSULTANT TOPOLOGIE                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│                         ┌─────────────┐                         │
│                         │    USER     │                         │
│                         └──────┬──────┘                         │
│                                │                                │
│                                ▼                                │
│                    ┌───────────────────────┐                    │
│                    │   META-CONSULTANT     │                    │
│                    │   (Orchestrator)      │                    │
│                    │                       │                    │
│                    │   • Analysiert Request│                    │
│                    │   • Wählt Domains     │                    │
│                    │   • Moderiert Meeting │                    │
│                    │   • Schreibt Spec     │                    │
│                    └───────────┬───────────┘                    │
│                                │                                │
│              ┌─────────────────┼─────────────────┐              │
│              │                 │                 │              │
│              ▼                 ▼                 ▼              │
│     ┌─────────────┐   ┌─────────────┐   ┌─────────────┐        │
│     │ PDM-EXPERT  │   │ ERP-EXPERT  │   │ INFRA-EXPERT│        │
│     │             │   │             │   │             │        │
│     │ CLAUDE.md   │   │ CLAUDE.md   │   │ CLAUDE.md   │        │
│     │ + PDM-Skills│   │ + ERP-Skills│   │ + Infra-Skil│        │
│     └──────┬──────┘   └──────┬──────┘   └──────┬──────┘        │
│            │                 │                 │                │
│            └─────────────────┼─────────────────┘                │
│                              │                                  │
│                              ▼                                  │
│                    ┌───────────────────┐                        │
│                    │  meeting-state.json│                        │
│                    │                   │                        │
│                    │  • Fragen         │                        │
│                    │  • Antworten      │                        │
│                    │  • Konsens        │                        │
│                    │  • Offene Punkte  │                        │
│                    └───────────────────┘                        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Agentic Meeting Ablauf

```
┌─────────────────────────────────────────────────────────────────┐
│  ROUND 1: Domain-Experten analysieren (parallel)               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   PDM-Expert                ERP-Expert              Infra-Expert │
│   ──────────                ──────────              ───────────  │
│   Liest PDM-Docs            Liest ERP-Docs         Liest Infra  │
│   Schreibt →                Schreibt →             Schreibt →   │
│   pdm-analysis.json         erp-analysis.json      infra.json   │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│  ROUND 2: Meta-Consultant synthetisiert                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   Meta-Consultant liest alle *-analysis.json                    │
│   Identifiziert Konflikte, Abhängigkeiten                       │
│   Schreibt → synthesis.json (oder stellt Rückfragen an User)    │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│  ROUND 3: Rückfragen (falls nötig)                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   Meta-Consultant: "Der PDM-Expert sagt X, ERP sagt Y.          │
│                     Wie sollen wir das lösen?"                  │
│   User: "Mach X"                                                │
│   Meta-Consultant: Aktualisiert synthesis.json                  │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│  ROUND 4: Spec + Phasen-Definition                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   Meta-Consultant schreibt:                                     │
│   • spec.yaml (WAS gebaut wird)                                 │
│   • phases.yaml (WIE der Workflow aussieht)                     │
│   • quality-gates.yaml (WANN ist eine Phase fertig)             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Implementierung: Claude Code Instanzen

```
phases/01-consultant/
├── CLAUDE.md                    # Meta-Consultant Prompt
├── meeting/
│   ├── round-1/
│   │   ├── pdm-expert/
│   │   │   ├── CLAUDE.md        # PDM-Expert Prompt
│   │   │   ├── skills/          # PDM-spezifische Skills
│   │   │   └── output/
│   │   │       └── analysis.json
│   │   ├── erp-expert/
│   │   │   ├── CLAUDE.md
│   │   │   └── output/
│   │   │       └── analysis.json
│   │   └── infra-expert/
│   │       └── ...
│   │
│   ├── round-2/
│   │   └── synthesis.json       # Meta-Consultant Output
│   │
│   └── round-3/                 # Falls Rückfragen
│       └── clarifications.json
│
├── output/
│   ├── spec.yaml                # Finale Spec
│   ├── phases.yaml              # Dynamische Phasen-Definition
│   └── quality-gates.yaml       # Gate-Definitionen
│
└── logs/
    └── meeting-transcript.md    # Vollständiger Verlauf
```

---

## 2. Multi-Provider LLM Support

### Die Entscheidung

```yaml
# config/llm-providers.yaml

default_provider: openrouter

providers:
  openrouter:
    base_url: "https://openrouter.ai/api/v1"
    api_key_env: "OPENROUTER_API_KEY"
    models:
      default: "openai/gpt-4o"
      reasoning: "anthropic/claude-sonnet-4"
      fast: "openai/gpt-4o-mini"
      
  anthropic:
    base_url: "https://api.anthropic.com/v1"
    api_key_env: "ANTHROPIC_API_KEY"
    models:
      default: "claude-sonnet-4-20250514"
      
  openai:
    base_url: "https://api.openai.com/v1"
    api_key_env: "OPENAI_API_KEY"
    models:
      default: "gpt-4o"
      
  xai:
    base_url: "https://api.x.ai/v1"
    api_key_env: "XAI_API_KEY"
    models:
      default: "grok-2"

# Migration von v3:
# cp /home/aiuser01/helix-v3/.env /home/aiuser01/helix-v4/.env
```

### Provider-Auswahl pro Phase

```yaml
# In phases.yaml kann pro Phase ein Provider gewählt werden:

phases:
  - name: "consultant"
    provider: "openrouter"
    model: "anthropic/claude-sonnet-4"  # Braucht gutes Reasoning
    
  - name: "developer"
    provider: "openrouter"
    model: "anthropic/claude-sonnet-4"  # Code-Qualität wichtig
    
  - name: "reviewer"
    provider: "openrouter"
    model: "openai/gpt-4o"  # Anderer Blickwinkel!
```

---

## 3. Dynamische Projekt-Struktur

### Die Entscheidung

Der Consultant definiert die Phasen dynamisch via `phases.yaml`:

```yaml
# phases.yaml - Vom Consultant generiert

project:
  name: "bom-export-csv"
  type: "feature"  # feature | documentation | research | bugfix
  
phases:
  - id: "01-consultant"
    name: "Anforderungsanalyse"
    type: "meeting"
    experts: ["pdm", "data-export"]
    output: "spec.yaml"
    
  - id: "02-developer"
    name: "Implementation"
    type: "development"
    template: "developer/python"
    skills: ["python-patterns", "csv-handling", "pdm-bom"]
    output: "src/"
    quality_gate:
      type: "files_exist"
      check: ["src/exporters/bom_csv.py", "tests/test_bom_csv.py"]
      on_failure: "retry"
      max_retries: 3
      
  - id: "03-reviewer"
    name: "Code Review"
    type: "review"
    template: "reviewer/code"
    input: "phases/02-developer/src/"
    output: "review.json"
    quality_gate:
      type: "review_approved"
      on_failure: "escalation"
      
  - id: "04-documentation"
    name: "Dokumentation"
    type: "documentation"
    template: "documentation/technical"
    output: "docs/"
    quality_gate:
      type: "files_exist"
      check: ["docs/bom-export.md"]

# Für ein Doku-Only Projekt:
# phases:
#   - id: "01-consultant"
#     type: "meeting"
#   - id: "02-writer"
#     type: "documentation"
#     template: "documentation/user"
#   - id: "03-reviewer"
#     type: "review"
#     template: "reviewer/documentation"
```

### Projekt-Typ Templates

```
templates/project-types/
├── feature.yaml           # Standard: Consultant → Dev → Review → Docs
├── documentation.yaml     # Consultant → Writer → Review
├── research.yaml          # Consultant → Researcher → Summary
├── bugfix.yaml            # Analyse → Fix → Test → Review
└── migration.yaml         # Analyse → Plan → Migrate → Verify
```

---

## 4. Spec Schema (Minimal)

```yaml
# spec.yaml - Minimales Schema

meta:
  id: string              # REQUIRED - Eindeutige ID
  domain: string          # REQUIRED - Haupt-Domain (pdm, erp, etc.)
  language: string        # OPTIONAL - Auto-detected aus files
  type: string            # OPTIONAL - feature, bugfix, docs (default: feature)
  
implementation:
  summary: string         # REQUIRED - Was wird gebaut (1-2 Sätze)
  files_to_create:        # REQUIRED - Liste der zu erstellenden Dateien
    - path: string
      description: string
  files_to_modify:        # OPTIONAL - Bestehende Dateien
    - path: string
      change: string
  acceptance_criteria:    # REQUIRED - Wann ist es fertig?
    - string
    
context:                  # OPTIONAL
  relevant_docs: [string]
  dependencies: [string]
  
# Beispiel:
meta:
  id: "bom-export-001"
  domain: "pdm"

implementation:
  summary: "BOM Export nach CSV mit Revision-History"
  files_to_create:
    - path: "src/exporters/bom_csv.py"
      description: "Hauptmodul für BOM-Export"
    - path: "tests/test_bom_csv.py"
      description: "Unit Tests"
  acceptance_criteria:
    - "CSV enthält alle BOM-Felder"
    - "Revision-History ist enthalten"
    - "Tests sind grün"
```

---

## 5. Quality Gate Failure + Live-Austausch

### Retry-Logik

```python
# quality_gates.py

async def run_phase_with_retry(phase_config: dict, project_dir: Path):
    max_retries = phase_config.get("quality_gate", {}).get("max_retries", 3)
    
    for attempt in range(max_retries):
        # Phase ausführen
        result = await run_claude_phase(phase_dir)
        
        # Quality Gate prüfen
        gate_result = check_quality_gate(phase_config, project_dir)
        
        if gate_result.passed:
            return result
        
        # Feedback für nächsten Versuch schreiben
        feedback_file = phase_dir / "feedback" / f"attempt-{attempt+1}.json"
        feedback_file.parent.mkdir(exist_ok=True)
        feedback_file.write_text(json.dumps({
            "attempt": attempt + 1,
            "gate_result": gate_result.to_dict(),
            "message": f"Quality Gate failed: {gate_result.message}",
            "fix_hints": gate_result.details
        }, indent=2))
        
        # CLAUDE.md für Retry aktualisieren
        update_claude_md_for_retry(phase_dir, gate_result)
    
    # 3x fehlgeschlagen → Escalation
    return await escalation_meeting(phase_config, project_dir, gate_result)
```

### Escalation Meeting (Live JSON-Austausch)

```
phases/02-developer/
├── escalation/
│   ├── CLAUDE.md                    # Escalation-Prompt
│   │
│   ├── context/
│   │   ├── original-spec.yaml       # Was sollte gebaut werden
│   │   ├── developer-output/        # Was wurde gebaut (symlink)
│   │   ├── gate-failures.json       # Warum ist es fehlgeschlagen
│   │   └── attempts/                # Alle bisherigen Versuche
│   │
│   ├── discussion/
│   │   ├── consultant-input.json    # Consultant analysiert
│   │   ├── developer-response.json  # Developer erklärt
│   │   └── resolution.json          # Gemeinsame Entscheidung
│   │
│   └── output/
│       ├── updated-spec.yaml        # Falls Spec angepasst wird
│       └── action-plan.json         # Was als nächstes passiert
```

### Discussion JSON Format

```json
// consultant-input.json
{
  "analysis": "Der Developer hat die Datei erstellt, aber das Format ist falsch",
  "root_cause": "Spec war nicht präzise genug bzgl. CSV-Delimiter",
  "options": [
    {
      "id": "A",
      "description": "Spec präzisieren und Developer nochmal laufen lassen",
      "effort": "low"
    },
    {
      "id": "B", 
      "description": "Akzeptieren und Delimiter konfigurierbar machen",
      "effort": "medium"
    }
  ],
  "recommendation": "A",
  "question_for_user": "Welchen Delimiter soll der CSV-Export nutzen?"
}

// developer-response.json
{
  "acknowledgment": "Verstanden, Delimiter war nicht spezifiziert",
  "clarification": "Ich habe Semikolon genommen weil deutsche Excel-Versionen das erwarten",
  "preference": "B - Konfigurierbar wäre am flexibelsten"
}

// resolution.json (nach User-Input)
{
  "decision": "B",
  "spec_updates": {
    "acceptance_criteria": [
      "CSV-Delimiter ist konfigurierbar (default: Semikolon)"
    ]
  },
  "next_action": "retry_developer"
}
```

---

## 6. Template-Vererbung (Beispiel)

### 2-Ebenen Vererbung

```
templates/
├── developer/
│   ├── _base.md              # EBENE 1: Basis für ALLE Developer
│   ├── python.md             # EBENE 2: Python-spezifisch (extends _base)
│   ├── cpp.md                # EBENE 2: C++-spezifisch (extends _base)
│   └── go.md                 # EBENE 2: Go-spezifisch (extends _base)
```

### Konkretes Beispiel

```markdown
{# templates/developer/_base.md - EBENE 1 #}

# Developer

Du bist Developer für HELIX.

## Deine Aufgabe
{{ summary }}

## Zu erstellende Dateien
{% for file in files_to_create %}
- `{{ file.path }}`: {{ file.description }}
{% endfor %}

## Akzeptanzkriterien
{% for criterion in acceptance_criteria %}
- [ ] {{ criterion }}
{% endfor %}

{% block language_rules %}
{# Wird von Ebene 2 überschrieben #}
{% endblock %}

## Output
Erstelle `logs/result.json` wenn fertig.
```

```markdown
{# templates/developer/python.md - EBENE 2 #}

{% extends "_base.md" %}

{% block language_rules %}
## Python-Regeln

1. **Type Hints** überall
2. **Docstrings** im Google-Style
3. **pytest** für Tests
4. **PEP 8** Formatierung

### Beispiel
```python
def export_bom(bom_id: str, output_path: Path) -> bool:
    """Exportiert BOM nach CSV.
    
    Args:
        bom_id: Die BOM-ID
        output_path: Ziel-Pfad für CSV
        
    Returns:
        True wenn erfolgreich
    """
    ...
```
{% endblock %}
```

### Generiertes CLAUDE.md

```markdown
# Developer

Du bist Developer für HELIX.

## Deine Aufgabe
BOM Export nach CSV mit Revision-History

## Zu erstellende Dateien
- `src/exporters/bom_csv.py`: Hauptmodul für BOM-Export
- `tests/test_bom_csv.py`: Unit Tests

## Akzeptanzkriterien
- [ ] CSV enthält alle BOM-Felder
- [ ] Revision-History ist enthalten
- [ ] Tests sind grün

## Python-Regeln

1. **Type Hints** überall
2. **Docstrings** im Google-Style
3. **pytest** für Tests
4. **PEP 8** Formatierung

### Beispiel
```python
def export_bom(bom_id: str, output_path: Path) -> bool:
    ...
```

## Output
Erstelle `logs/result.json` wenn fertig.
```

**Das ist 2-Ebenen:** `_base.md` → `python.md` → fertiges CLAUDE.md

---

## 7. Consultant Iteration

### Die Regel

```
Der Consultant iteriert so lange bis der User sagt:
- "Fertig" / "OK" / "Passt" → Spec schreiben
- "Schreib auf" → Spec schreiben
- "Erstell ADR" → ADR schreiben statt Spec
- "Bugreport" → Bugfix-Record schreiben
- "Abbrechen" → Session beenden ohne Output
```

### Implementierung

```python
# consultant_session.py

TERMINATION_KEYWORDS = {
    "spec": ["fertig", "ok", "passt", "schreib auf", "erstell spec"],
    "adr": ["erstell adr", "mach adr", "adr schreiben"],
    "bugfix": ["bugreport", "bugfix", "bug aufschreiben"],
    "abort": ["abbrechen", "stop", "cancel"]
}

def detect_termination(user_message: str) -> tuple[str, bool]:
    """Erkennt ob User die Session beenden will."""
    
    msg_lower = user_message.lower()
    
    for action, keywords in TERMINATION_KEYWORDS.items():
        if any(kw in msg_lower for kw in keywords):
            return action, True
    
    return None, False
```

---

## 8. ADR Migration Prompt

### Prompt für neuen Chat

```markdown
# ADR Migration: HELIX v3 → v4

Du bist ein Architektur-Berater der ADRs von HELIX v3 nach v4 portiert.

## Kontext

HELIX v4 hat eine neue Architektur:
- Claude Code CLI statt eigene Agents
- CLAUDE.md + Templates statt SDK
- Datei-basierte Kommunikation statt EventBus
- Python Orchestrator statt LangGraph
- Dynamische Phasen via phases.yaml

## Deine Aufgabe

Lies das v3 ADR und entscheide:

1. **OBSOLET** - Konzept wird durch Claude Code / neue Architektur ersetzt
   → Kurze Begründung warum
   
2. **MIGRIEREN** - Konzept ist relevant, muss angepasst werden
   → Schreibe neues v4 ADR mit Anpassungen
   
3. **ÜBERNEHMEN** - Konzept ist 1:1 relevant
   → Kopiere mit minimalen Anpassungen

## v3 ADR Pfad
`/home/aiuser01/helix-v3/adr/`

## v4 ADR Pfad
`/home/aiuser01/helix-v4/adr/`

## Output Format

```yaml
migration_decision:
  v3_adr: "XXX-name.md"
  decision: "OBSOLET" | "MIGRIEREN" | "ÜBERNEHMEN"
  reasoning: "..."
  
  # Falls MIGRIEREN oder ÜBERNEHMEN:
  v4_adr_number: "0XX"
  v4_adr_title: "..."
  key_changes:
    - "..."
```

## Starte mit

Welches v3 ADR soll ich analysieren?
```

---

## Zusammenfassung der Entscheidungen

| # | Thema | Entscheidung |
|---|-------|--------------|
| 1 | Consultant Topologie | Meta-Consultant + Domain-Experten, Agentic Meetings via JSON |
| 2 | LLM Provider | OpenRouter default, Multi-Provider via config, v3 .env übernehmen |
| 3 | Projekt-Struktur | Dynamisch via phases.yaml, Consultant definiert Phasen + Gates |
| 4 | Spec Schema | Minimal: meta + implementation + optional context |
| 5 | QG Failure | 3x Retry, dann Escalation Meeting mit JSON-Austausch |
| 6 | Templates | 2-Ebenen: _base.md → {language}.md |
| 7 | Consultant Ende | User sagt "fertig", "ADR erstellen", oder "abbrechen" |
| 8 | ADR Migration | Prompt bereitgestellt für neue Chats |

---

*Erstellt: 2025-12-21*
*Alle MUSS-Entscheidungen getroffen!*
