# Skill: Evolution Projects

> **Für Claude Code Instanzen** die an Evolution-Projekten arbeiten.

---

## Was ist ein Evolution-Projekt?

Ein **Evolution-Projekt** ermöglicht HELIX v4 sich selbst zu modifizieren und zu erweitern.
Änderungen werden zuerst in einem isolierten Test-System validiert bevor sie in Produktion
integriert werden.

**Kern-Prinzip: ADR als Single Source of Truth**

```
┌─────────────────────────────────────────────────────────────────┐
│                    ADR (Single Source of Truth)                  │
│                                                                 │
│  YAML Header:                    Markdown Sections:             │
│  • title, status                 • Kontext (Warum?)             │
│  • component_type                • Entscheidung (Was?)          │
│  • files.create                  • Implementation (Wie?)        │
│  • files.modify                  • Akzeptanzkriterien (Fertig?) │
│  • files.docs                    • Konsequenzen (Auswirkung?)   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Abgeleitete Artefakte                        │
│                                                                 │
│  • phases.yaml      - Ausführungsplan                           │
│  • Quality Gates    - Verifikationsregeln                       │
│  • Templates        - Claude-Instruktionen mit erwarteten Files │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Projekt-Struktur

Evolution-Projekte leben unter `projects/evolution/{name}/`:

```
projects/evolution/{name}/
├── ADR-{name}.md          # Single Source of Truth
├── phases.yaml            # Phasen-Definition
├── status.json            # Aktueller Status
├── phases/
│   ├── 1/
│   │   ├── CLAUDE.md      # Generierte Instruktionen
│   │   └── output/        # Phase-Output
│   │       ├── new/       # Neue Dateien
│   │       └── modified/  # Modifizierte Dateien
│   ├── 2/
│   └── ...
├── new/                   # Konsolidierte neue Dateien
└── modified/              # Konsolidierte modifizierte Dateien
```

---

## Workflow

### Phase 0: Consultant

Der Consultant erstellt das ADR und phases.yaml:

**Input:** User Request / Feature-Idee

**Output:**
- `ADR-{name}.md` - Vollständiges ADR mit allen Sections
- `phases.yaml` - Phasen-Definition

**Quality Gate:** ADR-System validiert:
- ADR gültig gegen Template?
- files.create/modify definiert?
- Akzeptanzkriterien vorhanden?

### Phase 1-N: Development

Jede Phase implementiert einen Teil des ADRs:

**Input:**
- ADR-{name}.md
- Output vorheriger Phasen

**Output:**
- Code in `output/new/` (für neue Dateien)
- Code in `output/modified/` (für geänderte Dateien)

**Quality Gate:** ADR-basierte Verifikation:
- Alle erwarteten Files existieren?
- Syntax-Check bestanden?
- Tests bestanden?

### Integration

Nach allen Phasen:

```
Deploy    → Copy to test system
Validate  → Run full test suite
Integrate → Copy to production (if tests pass)
```

**Final Gate:**
- Alle Tests bestehen?
- ADR.files.docs aktualisiert?
- Alle Akzeptanzkriterien checked?

---

## ADR für Evolution-Projekte

### Pflicht-Felder im YAML Header

```yaml
---
adr_id: "012"
title: "Feature Name"
status: Proposed

component_type: TOOL    # TOOL|NODE|AGENT|PROCESS|SERVICE|...
classification: NEW     # NEW|UPDATE|FIX|REFACTOR
change_scope: major     # major|minor|config|docs|hotfix

files:
  create:
    - src/helix/new_module.py
    - tests/test_new_module.py
  modify:
    - src/helix/existing.py
  docs:
    - docs/FEATURE.md
    - skills/helix/feature/SKILL.md

depends_on: []          # Vorherige ADRs
---
```

### Pflicht-Sections

```markdown
## Kontext
Warum wird diese Änderung benötigt?

## Entscheidung
Was wird entschieden?

## Implementation
Wie wird es umgesetzt? (Code-Beispiele)

## Dokumentation
Welche Docs müssen aktualisiert werden?

## Akzeptanzkriterien
- [ ] Kriterium 1
- [ ] Kriterium 2
- [ ] Dokumentation aktualisiert

## Konsequenzen
### Positiv
### Negativ
```

---

## Output-Regeln

### Verzeichnis-Struktur

Schreibe deine Outputs relativ zum Zielort im HELIX-Projekt:

```
phases/{n}/output/
├── new/              # Neue Dateien (files.create)
│   └── src/helix/...
└── modified/         # Geänderte Dateien (files.modify)
    └── src/helix/...
```

**Beispiel:**

Wenn ADR definiert:
```yaml
files:
  create:
    - src/helix/tools/new_tool.py
  modify:
    - src/helix/api/routes.py
```

Schreibst du:
```
output/new/src/helix/tools/new_tool.py
output/modified/src/helix/api/routes.py
```

### Was gehört wohin?

| ADR-Feld | Output-Verzeichnis |
|----------|-------------------|
| `files.create` | `output/new/{path}` |
| `files.modify` | `output/modified/{path}` |

---

## Templates und ADR-Integration

Developer-Templates zeigen automatisch die erwarteten Files aus dem ADR:

```markdown
## Expected Output Files

Create these files (from ADR):
- `src/helix/tools/new_tool.py`
- `tests/test_new_tool.py`

Modify these existing files:
- `src/helix/api/routes.py`
```

Diese Information kommt aus den Template-Variablen:
- `adr_files_create` - Liste aus ADR files.create
- `adr_files_modify` - Liste aus ADR files.modify

---

## Quality Gates

### ADR-basierte Verifikation

Nach jeder Phase prüft das System:

1. **File Existence**: Alle files aus `phase.output` existieren
2. **Path Resolution**: Sucht in `output/new/`, `output/modified/`, Phase-Dir
3. **Syntax Validation**: Python-Files via AST geprüft

### Retry-Mechanismus

- **Max 2 Retries** pro Phase
- Bei Fehler: `VERIFICATION_ERRORS.md` mit Details
- Claude liest Error-File und fixt Issues
- Nach 2 fehlgeschlagenen Retries: Phase FAILED

### Manuelle Verifikation

Du kannst vor Abschluss verifizieren:

```bash
python -m helix.tools.verify_phase
```

---

## Status-Flow

```
PENDING → DEVELOPING → READY → DEPLOYED → VALIDATED → INTEGRATED
                              ↓           ↓
                           FAILED ← ← ← ROLLBACK
```

| Status | Bedeutung |
|--------|-----------|
| `PENDING` | Projekt erstellt, noch nicht gestartet |
| `DEVELOPING` | Phasen werden ausgeführt |
| `READY` | Alle Phasen abgeschlossen |
| `DEPLOYED` | Im Test-System deployed |
| `VALIDATED` | Tests im Test-System bestanden |
| `INTEGRATED` | In Produktion übernommen |
| `FAILED` | Deployment oder Validation fehlgeschlagen |
| `ROLLBACK` | Wurde zurückgerollt |

---

## API Endpoints

| Endpoint | Method | Zweck |
|----------|--------|-------|
| `/helix/evolution/projects` | GET | Alle Projekte auflisten |
| `/helix/evolution/projects/{name}` | GET | Projekt-Details |
| `/helix/evolution/projects/{name}/deploy` | POST | Deploy to test |
| `/helix/evolution/projects/{name}/validate` | POST | Run validation |
| `/helix/evolution/projects/{name}/integrate` | POST | Integrate to prod |
| `/helix/evolution/projects/{name}/run` | POST | Full pipeline |

---

## Best Practices

### 1. ADR zuerst lesen

Bevor du mit der Arbeit beginnst:

```
1. Lies ADR-{name}.md
2. Verstehe files.create und files.modify
3. Lies die Akzeptanzkriterien
4. Dann erst implementieren
```

### 2. Konsistenz mit ADR

Stelle sicher dass:
- Alle `files.create` Dateien erstellt werden
- Alle `files.modify` Dateien geändert werden
- Output-Pfade dem ADR entsprechen

### 3. Inkrementelle Akzeptanz

Nach jeder Phase:
- Prüfe welche Akzeptanzkriterien erfüllt sind
- Dokumentiere offene Punkte
- Kommuniziere Fortschritt

### 4. Dokumentation mitliefern

Wenn ADR `files.docs` definiert:
- Erstelle/update diese Dokumentation
- Skills, Architecture-Docs, etc.

---

## Häufige Fehler

### 1. Falscher Output-Pfad

❌ `output/new_tool.py`
✅ `output/new/src/helix/tools/new_tool.py`

### 2. ADR nicht gelesen

❌ Eigene Interpretation was zu tun ist
✅ Genau dem ADR folgen

### 3. Akzeptanzkriterien ignoriert

❌ "Ist fertig weil Code existiert"
✅ Jedes Kriterium explizit prüfen

### 4. Verifikation übersprungen

❌ Phase abschließen ohne verify_phase
✅ `python -m helix.tools.verify_phase` vor Abschluss

---

## Checkliste für Phase-Abschluss

Bevor du eine Phase abschließt:

- [ ] Alle Files aus ADR.files.create existieren in `output/new/`
- [ ] Alle Files aus ADR.files.modify existieren in `output/modified/`
- [ ] `python -m helix.tools.verify_phase` läuft erfolgreich
- [ ] Python-Syntax ist valide
- [ ] Tests (falls vorhanden) sind grün
- [ ] Relevante Akzeptanzkriterien sind erfüllt

---

## Referenzen

- [ADR-012: ADR als Single Source of Truth](../../../adr/012-adr-as-single-source-of-truth.md)
- [docs/ARCHITECTURE-EVOLUTION.md](../../../docs/ARCHITECTURE-EVOLUTION.md)
- [skills/helix/adr/SKILL.md](../adr/SKILL.md) - ADR-Erstellung

---

*Skill Version: 1.0*
*Erstellt: 2025-12-22*
*ADR: ADR-012*
