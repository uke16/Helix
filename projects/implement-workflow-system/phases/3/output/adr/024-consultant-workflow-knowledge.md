---
adr_id: "024"
title: Consultant Workflow-Wissen
status: Proposed

project_type: helix_internal
component_type: PROMPT
classification: UPDATE
change_scope: minor

files:
  modify:
    - templates/consultant/session.md.j2
  create:
    - templates/consultant/workflow-guide.md
  docs:
    - docs/WORKFLOW-SYSTEM.md

depends_on:
  - ADR-023  # Workflow-Definitionen
---

# ADR-024: Consultant Workflow-Wissen

## Status

📋 Proposed

---

## Kontext

### Was ist das Problem?

Der Consultant (Meta-Consultant) kennt die neuen Workflow-Templates (ADR-023) nicht. Er kann keine Workflows starten und weiß nicht, wie er zwischen intern/extern und simple/complex unterscheiden soll.

### Warum muss es gelöst werden?

- Consultant muss wissen welche Workflows existieren
- Er muss den richtigen Workflow für ein Projekt wählen können
- Er muss Workflows via HELIX API starten können

### Was passiert wenn wir nichts tun?

- Consultant erstellt manuell Phasen ohne klare Struktur
- Inkonsistente Projekt-Setups
- Keine Nutzung der Workflow-Templates

---

## Entscheidung

### Wir entscheiden uns für:

Erweiterung des Consultant Templates `session.md.j2` um eine Workflow-Sektion und Erstellung eines detaillierten Workflow-Guides.

### Diese Entscheidung beinhaltet:

1. Neue Sektion "Workflows starten" in `session.md.j2`
2. Detaillierter `workflow-guide.md` als Referenz
3. Klare Entscheidungslogik: intern/extern, simple/complex

### Warum diese Lösung?

- Consultant lernt durch Template-Inhalt
- Workflow-Wissen ist im Kontext verfügbar
- Keine Code-Änderungen nötig, nur Prompt-Erweiterung

---

## Implementation

### 1. Erweiterung `session.md.j2`

Neue Sektion nach "ADR Tools":

```jinja2
---

## 🚀 Workflows starten

### Verfügbare Workflows

| Projekt-Typ | Workflow | Wann nutzen |
|-------------|----------|-------------|
| Intern + Leicht | `intern-simple` | HELIX Feature, klar definiert |
| Intern + Komplex | `intern-complex` | HELIX Feature, unklar/groß |
| Extern + Leicht | `extern-simple` | Externes Tool, klar definiert |
| Extern + Komplex | `extern-complex` | Externes Tool, unklar/groß |

### Workflow wählen

1. **Intern vs Extern?**
   - **Intern**: Ändert HELIX selbst (src/helix/, adr/, skills/)
   - **Extern**: Separates Projekt (projects/external/)
   - *Wenn unklar: Frage den User*

2. **Leicht vs Komplex?**
   - **Leicht**: Scope ist klar, <5 Files, 1-2 Sessions
   - **Komplex**: Scope unklar, braucht Feasibility/Planning
   - *User kann es sagen, oder du schätzt*

### Workflow starten

```bash
# 1. Projekt-Verzeichnis erstellen
mkdir -p projects/{internal|external}/{name}/phases

# 2. phases.yaml aus Template kopieren
cp templates/workflows/{workflow}.yaml projects/.../phases.yaml

# 3. Via API starten
curl -X POST http://localhost:8001/helix/execute \
  -H "Content-Type: application/json" \
  -d '{"project_path": "projects/.../", "phase": 1}'

# 4. Status prüfen
curl http://localhost:8001/helix/jobs
```

### Phase Reset (bei Fehlern)

```bash
# Phase zurücksetzen und neu starten
curl -X POST http://localhost:8001/helix/execute \
  -d '{"project_path": "...", "phase": N, "reset": true}'
```
```

### 2. Neuer Guide `workflow-guide.md`

Detaillierte Anleitung mit Beispiel-Dialogen und Troubleshooting.

---

## Dokumentation

### Zu aktualisierende Dokumente

| Dokument | Änderung |
|----------|----------|
| `templates/consultant/session.md.j2` | Workflow-Sektion hinzufügen |
| `templates/consultant/workflow-guide.md` | Neues Dokument |
| `docs/WORKFLOW-SYSTEM.md` | Referenz auf Guide hinzufügen |

---

## Akzeptanzkriterien

### 1. Template-Erweiterung

- [x] Neue "Workflows starten" Sektion in session.md.j2
- [x] Alle 4 Workflows dokumentiert
- [x] Entscheidungslogik erklärt (intern/extern, simple/complex)

### 2. API-Integration

- [x] /helix/execute Endpoint dokumentiert
- [x] /helix/jobs Endpoint dokumentiert
- [x] Phase Reset dokumentiert

### 3. Workflow-Guide

- [x] workflow-guide.md erstellt
- [x] Beispiel-Dialoge enthalten
- [x] Troubleshooting enthalten

---

## Konsequenzen

### Vorteile

- Consultant weiß automatisch über Workflows Bescheid
- Konsistente Projekt-Starts
- API-Nutzung ist dokumentiert

### Nachteile / Risiken

- Template wird länger (mehr Tokens im Kontext)
- Consultant muss die richtigen Fragen stellen

### Mitigation

- Workflow-Guide als separate Datei (nur bei Bedarf lesen)
- Klare Entscheidungslogik minimiert Rückfragen

---

## Referenzen

- ADR-023: Workflow-Definitionen
- `src/helix/api/routes/helix.py`: API Implementation
- `docs/ROADMAP-CONSULTANT-WORKFLOWS.md`: Gap-Analyse
