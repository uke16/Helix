# HELIX Self-Documentation Prinzip

> **Jede Änderung dokumentiert sich selbst.**
> Keine Änderung ist fertig bis die Dokumentation aktualisiert ist.

---

## Warum ist das wichtig?

HELIX orchestriert **Claude Code Instanzen** die die Dokumentation lesen um zu verstehen wie sie arbeiten sollen.

```
┌─────────────────────────────────────────────────────────────┐
│  Problem ohne Self-Documentation:                          │
│                                                             │
│  Feature X wird implementiert                               │
│       ↓                                                     │
│  Dokumentation wird "später" gemacht (= nie)                │
│       ↓                                                     │
│  Nächste Claude Code Instanz weiß nichts von Feature X     │
│       ↓                                                     │
│  Feature X wird ignoriert oder falsch verwendet             │
└─────────────────────────────────────────────────────────────┘
```

```
┌─────────────────────────────────────────────────────────────┐
│  Mit Self-Documentation:                                    │
│                                                             │
│  Feature X wird implementiert                               │
│       ↓                                                     │
│  Phase "Documentation Update" aktualisiert alle Docs        │
│       ↓                                                     │
│  Nächste Claude Code Instanz liest aktualisierte Docs       │
│       ↓                                                     │
│  Feature X wird korrekt verwendet                           │
└─────────────────────────────────────────────────────────────┘
```

---

## Die 4 Dokumentations-Ebenen

| Ebene | Zielgruppe | Dateien | Wann aktualisieren? |
|-------|------------|---------|---------------------|
| **1. Top-Level** | Mensch & Claude | `README.md`, `ONBOARDING.md`, `CLAUDE.md` | Neue Features, Workflow-Änderungen |
| **2. Architecture** | Entwickler | `docs/*.md` | Neue Module, Architektur-Entscheidungen |
| **3. Skills** | Claude Code | `skills/*/SKILL.md` | Neues Domain-Wissen, Best Practices |
| **4. Docstrings** | Code-Leser | Im Code selbst | Jede public Function/Class |

### Ebene 1: Top-Level

**Wer liest das?** Menschen die HELIX verstehen wollen + Claude Code Instanzen

| Datei | Zweck | Aktualisieren wenn... |
|-------|-------|----------------------|
| `README.md` | Projekt-Übersicht | Key Features ändern |
| `ONBOARDING.md` | Konzept-Erklärung | Neue Konzepte/Workflows |
| `CLAUDE.md` | Arbeitsanweisungen für Claude | Neue Regeln, Quality Gates |

### Ebene 2: Architecture Docs

**Wer liest das?** Entwickler die HELIX erweitern

| Datei | Zweck |
|-------|-------|
| `docs/ARCHITECTURE-MODULES.md` | Alle Python-Module beschrieben |
| `docs/ARCHITECTURE-DECISIONS.md` | Warum-Entscheidungen |
| `docs/CONCEPT.md` | High-Level Konzept |
| `docs/*-CONCEPT.md` | Feature-spezifische Konzepte |

### Ebene 3: Skills

**Wer liest das?** Claude Code Instanzen während der Ausführung

```
skills/
├── helix/           # Wie HELIX funktioniert
│   ├── SKILL.md
│   └── adr/         # ADR-spezifisches Wissen
│       └── SKILL.md
├── pdm/             # PDM System Wissen
├── encoder/         # Encoder Produkt-Wissen
└── infrastructure/  # Docker, DB, etc.
```

**Skill-Struktur:**
```markdown
# [Topic] Skill

## Kontext
Wann ist dieses Wissen relevant?

## Kernkonzepte
Was muss man verstehen?

## Best Practices
Wie macht man es richtig?

## Beispiele
Konkrete Code-Beispiele

## Anti-Patterns
Was sollte man vermeiden?
```

### Ebene 4: Docstrings

**Wer liest das?** IDE, andere Entwickler, AI-Tools

```python
class ADRParser:
    """Parse ADR documents in v2 format.
    
    The parser extracts:
    - YAML frontmatter with metadata
    - Markdown sections
    - Acceptance criteria checkboxes
    
    Example:
        parser = ADRParser()
        adr = parser.parse_file(Path("adr/001-feature.md"))
        print(adr.metadata.title)
    
    See Also:
        - ADRValidator for validation
        - docs/ADR-TEMPLATE.md for the template
    """
```

---

## Self-Documentation in der Praxis

### Jedes CONCEPT.md braucht eine Dokumentations-Section

```markdown
## Dokumentation

### Zu aktualisierende Dateien

| Ebene | Datei | Änderung |
|-------|-------|----------|
| **Top-Level** | `CLAUDE.md` | Neue Regel X dokumentieren |
| **Architecture** | `docs/ARCHITECTURE-MODULES.md` | Modul Y hinzufügen |
| **Skills** | `skills/domain/SKILL.md` | NEU: Wissen Z |
| **Docstrings** | Im Code | Alle public APIs |
```

### Jede phases.yaml braucht eine Documentation-Phase

```yaml
phases:
  # ... development phases ...
  
  - id: "N"
    name: Documentation Update
    type: documentation
    description: |
      Update all documentation per Self-Documentation principle.
      Lies CONCEPT.md Section "Dokumentation" für die Liste.
    
    output:
      - modified/CLAUDE.md
      - modified/docs/ARCHITECTURE-MODULES.md
      - new/skills/topic/SKILL.md
```

### Quality Gate für Dokumentation

```yaml
quality_gate:
  type: files_exist
  files:
    - modified/docs/ARCHITECTURE-MODULES.md
    - new/skills/topic/SKILL.md
```

---

## Checkliste: Ist meine Änderung vollständig dokumentiert?

- [ ] **CONCEPT.md** hat eine "Dokumentation" Section
- [ ] **phases.yaml** hat eine Documentation-Phase
- [ ] **ARCHITECTURE-MODULES.md** beschreibt neue Module
- [ ] **Skills** existieren für neues Domain-Wissen
- [ ] **CLAUDE.md** erklärt neue Regeln/Quality Gates
- [ ] **Docstrings** sind für alle public APIs vorhanden
- [ ] **ONBOARDING.md** ist aktuell (falls Workflow-Änderung)

---

## Konsequenzen

**Vorteile:**
- Claude Code Instanzen verstehen immer den aktuellen Stand
- Keine "vergessene" Dokumentation
- Konsistenz über alle Features
- Quality Gates können Dokumentation prüfen

**Aufwand:**
- Jede Änderung braucht ~10-20% mehr Zeit für Doku
- Documentation-Phase in jeder phases.yaml

**Trade-off ist es wert** weil HELIX auf Claude Code Instanzen basiert die die Dokumentation lesen müssen.
