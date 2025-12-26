---
adr_id: "023"
title: Workflow-Definitionen für Projekt-Matrix
status: Proposed

project_type: helix_internal
component_type: CONFIG
classification: NEW
change_scope: major

files:
  create:
    - templates/workflows/intern-simple.yaml
    - templates/workflows/intern-complex.yaml
    - templates/workflows/extern-simple.yaml
    - templates/workflows/extern-complex.yaml
  docs:
    - docs/WORKFLOW-SYSTEM.md
    - skills/helix/workflows.md

depends_on:
  - ADR-017  # Phase Orchestrator
  - ADR-022  # Unified API Architecture
---

# ADR-023: Workflow-Definitionen für Projekt-Matrix

## Status

📋 Proposed

---

## Kontext

### Was ist das Problem?

HELIX unterscheidet Projekte nach zwei Dimensionen:

1. **Projekt-Typ**: `helix_internal` (HELIX-Entwicklung) vs. `external` (Drittanbieter)
2. **Komplexität**: `simple` (lineare Phasen) vs. `complex` (dynamische Phasen)

Aktuell gibt es nur generische Projekt-Templates (`templates/project-types/feature.yaml`), die diese Matrix nicht abbilden. Der Consultant weiß nicht, welchen Workflow er für welches Projekt starten soll.

### Warum muss es gelöst werden?

- Interne Projekte brauchen Deploy-to-Test → E2E → Deploy-to-Prod
- Externe Projekte brauchen keinen HELIX-Deploy-Zyklus
- Komplexe Projekte brauchen dynamische Phasen-Generierung
- Sub-Agent Verifikation muss pro Phase konfigurierbar sein

### Was passiert wenn wir nichts tun?

- Consultant erstellt manuell Phasen ohne klare Struktur
- Inkonsistente Workflows zwischen Projekten
- Kein automatisches Deploy-Verify-Integrate für interne Projekte

---

## Entscheidung

### Wir entscheiden uns für:

4 dedizierte Workflow-Templates in `templates/workflows/` die alle Kombinationen der Projekt-Matrix abdecken.

### Diese Entscheidung beinhaltet:

1. `intern-simple.yaml`: Linearer Workflow mit vollständigem Deploy-Zyklus
2. `intern-complex.yaml`: Dynamische Phasen mit Deploy-Zyklus
3. `extern-simple.yaml`: Linearer Workflow ohne Deploy-Zyklus
4. `extern-complex.yaml`: Dynamische Phasen ohne Deploy-Zyklus

### Warum diese Lösung?

- Klare Trennung zwischen internen und externen Projekten
- Wiederverwendbare Workflow-Definitionen
- Consultant kann einfach den passenden Workflow auswählen
- Sub-Agent Verifikation ist pro Phase konfigurierbar

### Welche Alternativen wurden betrachtet?

1. **Ein generisches Template mit Conditionals**: Nicht gewählt weil zu komplex und schwer wartbar
2. **Workflow-Generierung zur Laufzeit**: Nicht gewählt weil weniger vorhersagbar und schwerer zu debuggen

---

## Implementation

### 1. Workflow-Template Struktur

**Neue Dateien:**

```
templates/workflows/
├── intern-simple.yaml
├── intern-complex.yaml
├── extern-simple.yaml
└── extern-complex.yaml
```

### 2. Template-Format

Jedes Workflow-Template hat folgende Struktur:

```yaml
# templates/workflows/intern-simple.yaml

name: intern-simple
description: Leichtes internes HELIX-Projekt
project_type: helix_internal
complexity: simple
max_retries: 3  # Sub-Agent Verifikation Retries

phases:
  - id: planning
    name: "Planning & ADR"
    type: consultant
    template: consultant/planning.md
    output:
      - "ADR-*.md"
      - "phases.yaml"
    quality_gate:
      type: adr_valid
    verify_agent: true

  - id: development
    type: development
    template: developer/python.md
    quality_gate:
      type: syntax_check
    verify_agent: true

  # ... weitere Phasen
```

### 3. Dynamische Phasen (Complex Workflows)

Complex Workflows unterstützen dynamische Phasen-Generierung:

```yaml
# templates/workflows/intern-complex.yaml

phases:
  - id: planning-agent
    type: planning
    generates_phases: true
    phase_config:
      min_phases: 1
      max_phases: 5
      phase_template: developer/python.md

  # Dynamische Phasen werden hier eingefügt

  - id: verify
    after_dynamic: true  # Kommt nach dynamischen Phasen
```

### 4. Projekt-Matrix Übersicht

| Workflow | Projekt-Typ | Komplexität | Deploy-Zyklus | Dynamische Phasen |
|----------|-------------|-------------|---------------|-------------------|
| `intern-simple` | helix_internal | simple | ✅ Test → E2E → Prod | ❌ |
| `intern-complex` | helix_internal | complex | ✅ Test → E2E → Prod | ✅ 1-5 |
| `extern-simple` | external | simple | ❌ | ❌ |
| `extern-complex` | external | complex | ❌ | ✅ 1-5 |

---

## Dokumentation

### Zu aktualisierende Dokumente

| Dokument | Änderung |
|----------|----------|
| `docs/WORKFLOW-SYSTEM.md` | Neues Dokument mit Workflow-Beschreibung |
| `skills/helix/workflows.md` | Aktualisieren mit neuen Workflow-Templates |
| `CLAUDE.md` | Referenz auf Workflow-Templates hinzufügen |

---

## Akzeptanzkriterien

### 1. Workflow-Templates

- [x] `intern-simple.yaml` existiert mit 7 Phasen (Planning → Deploy-Prod)
- [x] `intern-complex.yaml` existiert mit dynamischer Phasen-Generierung
- [x] `extern-simple.yaml` existiert mit 4 Phasen (ohne Deploy)
- [x] `extern-complex.yaml` existiert mit dynamischer Phasen-Generierung

### 2. Template-Struktur

- [x] Jedes Template hat: name, project_type, complexity, phases
- [x] Jede Phase hat: id, type, description, verify_agent
- [x] max_retries: 3 ist in allen Templates konfiguriert

### 3. Workflow-Eigenschaften

- [x] Interne Workflows haben Deploy-Zyklus (deploy-test, e2e, deploy-prod)
- [x] Externe Workflows haben keinen Deploy-Zyklus
- [x] Complex Workflows haben dynamische Phasen-Konfiguration

---

## Konsequenzen

### Vorteile

- Klare, vorhersagbare Workflows für alle Projekt-Typen
- Consultant kann einfach den richtigen Workflow wählen
- Sub-Agent Verifikation ist konsistent konfiguriert
- Dynamische Phasen ermöglichen flexible komplexe Projekte

### Nachteile / Risiken

- 4 Templates müssen synchron gehalten werden
- Änderungen an gemeinsamen Phasen müssen in mehreren Dateien erfolgen

### Mitigation

- Dokumentation der Template-Struktur in SKILL.md
- Potentiell: Gemeinsame Phase-Definitionen extrahieren (Future ADR)

---

## Referenzen

- ADR-017: Phase Orchestrator
- ADR-022: Unified API Architecture
- `docs/ROADMAP-CONSULTANT-WORKFLOWS.md`: Gap-Analyse
- `docs/ARCHITECTURE-ORCHESTRATOR.md`: Simple/Complex Konzept
