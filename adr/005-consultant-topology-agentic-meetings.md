# ADR-005: Consultant Topologie & Agentic Meetings

**Status:** Akzeptiert  
**Datum:** 2025-12-21  
**Bezug:** ADR-000, ADR-001

---

## Kontext

Der Consultant-Prozess muss komplexe Anforderungen analysieren können, 
die mehrere Domains betreffen. Ein einzelner Consultant reicht nicht.

---

## Entscheidung

### Meta-Consultant + Domain-Experten Architektur

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER                                    │
│                           │                                     │
│                           ▼                                     │
│              ┌────────────────────────┐                         │
│              │    META-CONSULTANT     │                         │
│              │    ─────────────────   │                         │
│              │    • Analysiert Request│                         │
│              │    • Wählt Experten    │                         │
│              │    • Moderiert Meeting │                         │
│              │    • Synthetisiert     │                         │
│              │    • Schreibt Output   │                         │
│              └───────────┬────────────┘                         │
│                          │                                      │
│        ┌─────────────────┼─────────────────┐                    │
│        │                 │                 │                    │
│        ▼                 ▼                 ▼                    │
│   ┌─────────┐       ┌─────────┐       ┌─────────┐              │
│   │   PDM   │       │   ERP   │       │  INFRA  │              │
│   │ EXPERT  │       │ EXPERT  │       │ EXPERT  │              │
│   └─────────┘       └─────────┘       └─────────┘              │
│        │                 │                 │                    │
│        └─────────────────┼─────────────────┘                    │
│                          ▼                                      │
│                  ┌───────────────┐                              │
│                  │ Gemeinsame    │                              │
│                  │ Analyse-JSONs │                              │
│                  └───────────────┘                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Verfügbare Domain-Experten

```yaml
# config/domain-experts.yaml

experts:
  pdm:
    name: "PDM Domain Expert"
    description: "Produktdatenmanagement, Stücklisten, Revisionen"
    skills:
      - "domains/pdm/structure.md"
      - "domains/pdm/bom.md"
      - "domains/pdm/revisions.md"
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
      - "domains/erp/integration.md"
      - "domains/erp/orders.md"
    triggers:
      - "sap"
      - "auftrag"
      - "bestellung"
      - "erp"
      
  infrastructure:
    name: "Infrastructure Expert"
    description: "Deployment, Docker, CI/CD"
    skills:
      - "tools/docker.md"
      - "tools/kubernetes.md"
      - "tools/ci-cd.md"
    triggers:
      - "deploy"
      - "docker"
      - "kubernetes"
      - "ci"
      - "pipeline"
      
  database:
    name: "Database Expert"
    description: "PostgreSQL, Migrations, Performance"
    skills:
      - "tools/postgresql.md"
      - "tools/migrations.md"
    triggers:
      - "datenbank"
      - "sql"
      - "migration"
      - "postgres"
      
  frontend:
    name: "Frontend Expert"
    description: "React, UI/UX, Web"
    skills:
      - "languages/typescript.md"
      - "tools/react.md"
    triggers:
      - "frontend"
      - "ui"
      - "react"
      - "web"
```

### Meeting-Ablauf

```
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 1: Request-Analyse (Meta-Consultant)                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Input: User-Request                                            │
│  "Ich brauche einen BOM-Export der auch SAP-Daten enthält"      │
│                                                                  │
│  Meta-Consultant:                                               │
│  1. Erkennt Keywords: "BOM" → PDM, "SAP" → ERP                  │
│  2. Wählt Experten: [pdm, erp]                                  │
│  3. Formuliert Fragen für jeden Experten                        │
│                                                                  │
│  Output: expert-selection.json                                  │
│  {                                                              │
│    "experts": ["pdm", "erp"],                                   │
│    "questions": {                                               │
│      "pdm": "Welche BOM-Felder sind relevant für Export?",      │
│      "erp": "Welche SAP-Felder müssen gemappt werden?"          │
│    }                                                            │
│  }                                                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 2: Experten-Analyse (Parallel)                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  PDM-Expert                         ERP-Expert                  │
│  ───────────                        ──────────                  │
│  Liest:                             Liest:                      │
│  • Domain-Skills                    • Domain-Skills             │
│  • Frage vom Meta                   • Frage vom Meta            │
│                                                                  │
│  Schreibt:                          Schreibt:                   │
│  pdm-analysis.json                  erp-analysis.json           │
│  {                                  {                           │
│    "fields": [...],                   "sap_fields": [...],      │
│    "constraints": [...],              "mapping_rules": [...],   │
│    "recommendations": [...]           "api_endpoints": [...]    │
│  }                                  }                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 3: Synthese (Meta-Consultant)                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Meta-Consultant liest alle *-analysis.json                     │
│                                                                  │
│  Prüft auf:                                                     │
│  • Konflikte zwischen Experten                                  │
│  • Fehlende Informationen                                       │
│  • Abhängigkeiten                                               │
│                                                                  │
│  Bei Konflikten/Unklarheiten:                                   │
│  → Rückfrage an User                                            │
│                                                                  │
│  Sonst:                                                         │
│  → Weiter zu Phase 4                                            │
│                                                                  │
│  Output: synthesis.json                                         │
│  {                                                              │
│    "combined_requirements": [...],                              │
│    "conflicts_resolved": [...],                                 │
│    "open_questions": []                                         │
│  }                                                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 4: Output-Generierung                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Meta-Consultant schreibt:                                      │
│                                                                  │
│  spec.yaml                                                      │
│  ─────────                                                      │
│  Das WAS: Features, Dateien, Kriterien                          │
│                                                                  │
│  phases.yaml                                                    │
│  ───────────                                                    │
│  Das WIE: Welche Phasen, welche Templates, welche Gates         │
│                                                                  │
│  quality-gates.yaml                                             │
│  ─────────────────                                              │
│  Das WANN: Gate-Definitionen, Failure-Handling                  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Verzeichnis-Struktur

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
│   │   ├── pdm-expert/
│   │   │   ├── CLAUDE.md            # Expert-spezifischer Prompt
│   │   │   ├── skills/              # Symlinks zu Domain-Skills
│   │   │   └── output/
│   │   │       └── analysis.json
│   │   │
│   │   ├── erp-expert/
│   │   │   ├── CLAUDE.md
│   │   │   ├── skills/
│   │   │   └── output/
│   │   │       └── analysis.json
│   │   │
│   │   └── ... (weitere Experten)
│   │
│   ├── phase-3-synthesis/
│   │   ├── all-analyses/            # Symlinks zu allen analysis.json
│   │   └── synthesis.json
│   │
│   └── phase-4-clarification/       # Falls Rückfragen nötig
│       ├── questions.json
│       └── user-answers.json
│
├── output/
│   ├── spec.yaml
│   ├── phases.yaml
│   └── quality-gates.yaml
│
└── logs/
    └── meeting-transcript.md
```

### Meta-Consultant CLAUDE.md Template

```markdown
# Meta-Consultant

Du bist der Meta-Consultant für HELIX v4.

## Deine Rolle

Du orchestrierst Agentic Meetings mit Domain-Experten.

## Verfügbare Experten

{% for expert in available_experts %}
### {{ expert.name }}
{{ expert.description }}
Triggers: {{ expert.triggers | join(", ") }}

{% endfor %}

## Dein Ablauf

### 1. Request analysieren
- Lies den User-Request in `input/request.md`
- Identifiziere relevante Domains
- Wähle passende Experten

### 2. Experten-Meeting starten
Für jeden gewählten Experten:
1. Erstelle Verzeichnis `meeting/phase-2-analysis/{expert}/`
2. Generiere CLAUDE.md mit spezifischer Frage
3. Führe Expert-Analyse aus (Claude Code in Subdir)

### 3. Synthese
- Lies alle `analysis.json` Dateien
- Identifiziere Konflikte oder Lücken
- Bei Unklarheiten: Frage User

### 4. Output generieren
Schreibe:
- `output/spec.yaml` - Was gebaut wird
- `output/phases.yaml` - Wie der Workflow aussieht
- `output/quality-gates.yaml` - Wann ist eine Phase fertig

## Aktueller Request

{{ user_request }}

## Output-Format

Erstelle am Ende `logs/meeting-transcript.md` mit dem vollständigen Ablauf.
```

### Expert CLAUDE.md Template

```markdown
# {{ expert_name }}

Du bist der {{ expert_name }} für HELIX.

## Dein Wissen

Lies die Dateien in `skills/` für dein Domain-Wissen:
{% for skill in skills %}
- `skills/{{ skill }}`
{% endfor %}

## Deine Aufgabe

{{ question_from_meta }}

## Context

Original-Request: {{ original_request }}

## Output

Schreibe deine Analyse in `output/analysis.json`:

```json
{
  "domain": "{{ domain }}",
  "findings": [...],
  "requirements": [...],
  "constraints": [...],
  "recommendations": [...],
  "dependencies": [...],
  "open_questions": [...]
}
```
```

---

## Implementierung

```python
# consultant_meeting.py

async def run_consultant_meeting(
    project_dir: Path,
    user_request: str,
    available_experts: dict
) -> ConsultantOutput:
    """Führt ein vollständiges Consultant Meeting durch."""
    
    consultant_dir = project_dir / "phases" / "01-consultant"
    consultant_dir.mkdir(parents=True, exist_ok=True)
    
    # Input speichern
    (consultant_dir / "input").mkdir(exist_ok=True)
    (consultant_dir / "input" / "request.md").write_text(user_request)
    
    # Phase 1: Request analysieren, Experten wählen
    expert_selection = await analyze_request_select_experts(
        request=user_request,
        available_experts=available_experts
    )
    
    meeting_dir = consultant_dir / "meeting"
    (meeting_dir / "phase-1-selection").mkdir(parents=True, exist_ok=True)
    (meeting_dir / "phase-1-selection" / "expert-selection.json").write_text(
        json.dumps(expert_selection, indent=2)
    )
    
    # Phase 2: Experten parallel analysieren lassen
    analysis_dir = meeting_dir / "phase-2-analysis"
    analysis_results = {}
    
    for expert_id in expert_selection["experts"]:
        expert_config = available_experts[expert_id]
        expert_dir = analysis_dir / f"{expert_id}-expert"
        
        # Expert-Verzeichnis vorbereiten
        await setup_expert_directory(
            expert_dir=expert_dir,
            expert_config=expert_config,
            question=expert_selection["questions"][expert_id],
            original_request=user_request
        )
        
        # Expert ausführen (Claude Code)
        result = await run_claude_phase(expert_dir)
        analysis_results[expert_id] = result
    
    # Phase 3: Synthese
    synthesis = await synthesize_analyses(
        analyses=analysis_results,
        original_request=user_request
    )
    
    (meeting_dir / "phase-3-synthesis").mkdir(exist_ok=True)
    (meeting_dir / "phase-3-synthesis" / "synthesis.json").write_text(
        json.dumps(synthesis, indent=2)
    )
    
    # Rückfragen an User falls nötig
    if synthesis.get("open_questions"):
        user_answers = await ask_user_questions(synthesis["open_questions"])
        synthesis = await update_synthesis_with_answers(synthesis, user_answers)
    
    # Phase 4: Output generieren
    output = await generate_consultant_output(synthesis, user_request)
    
    output_dir = consultant_dir / "output"
    output_dir.mkdir(exist_ok=True)
    (output_dir / "spec.yaml").write_text(yaml.dump(output["spec"]))
    (output_dir / "phases.yaml").write_text(yaml.dump(output["phases"]))
    (output_dir / "quality-gates.yaml").write_text(yaml.dump(output["quality_gates"]))
    
    return ConsultantOutput(**output)
```

---

## Konsequenzen

### Positiv
- Expertise wird skalierbar (neue Experten = neue Config)
- Parallele Analyse spart Zeit
- Strukturierte Konflikterkennung
- Volle Transparenz über Meeting-Verlauf

### Negativ
- Komplexer als Single-Consultant
- Mehr Claude Code Aufrufe (Kosten)
- Orchestrierung muss robust sein

---

## Referenzen

- ADR-000: Vision & Architecture
- ADR-001: Template & Context System
- HELIX v3 ADR-119: Multi-Domain Consultant

