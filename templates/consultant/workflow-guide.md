# HELIX Workflow Guide für Consultants

> Detaillierte Anleitung zum Starten und Verwalten von Workflows

---

## Workflow-Matrix

```
                    │  LEICHT (simple)       │  KOMPLEX (complex)
────────────────────┼────────────────────────┼────────────────────────────
                    │                        │
  INTERN            │  intern-simple         │  intern-complex
  (helix_internal)  │  Planning              │  Feasibility
                    │  → Development         │  → Planning (1-5 Steps)
                    │  → Verify              │  → [dynamische Phasen]
                    │  → Documentation       │  → Verify
                    │  → Deploy-Test         │  → Documentation
                    │  → E2E                 │  → Deploy-Test
                    │  → Deploy-Prod         │  → E2E → Deploy-Prod
────────────────────┼────────────────────────┼────────────────────────────
                    │                        │
  EXTERN            │  extern-simple         │  extern-complex
  (external)        │  Planning              │  Feasibility
                    │  → Development         │  → Planning (1-5 Steps)
                    │  → Verify              │  → [dynamische Phasen]
                    │  → Documentation       │  → Verify
                    │                        │  → Documentation
────────────────────┴────────────────────────┴────────────────────────────
```

---

## Entscheidungslogik

### 1. Intern oder Extern?

**Frage dem User wenn unklar:**
> "Betrifft dieses Feature HELIX selbst, oder ist es ein separates Projekt?"

**Intern (`helix_internal`)**:
- Ändert Dateien in `src/helix/`
- Erstellt/ändert ADRs in `adr/`
- Aktualisiert Skills in `skills/`
- Ändert Konfiguration in `config/`
- Betrifft Templates in `templates/`

**Extern (`external`)**:
- Eigenständiges Tool/Service
- Lebt in `projects/external/`
- Nutzt HELIX nur zur Orchestrierung
- Kein Deploy-to-Prod für HELIX

### 2. Leicht oder Komplex?

**Der User kann es sagen, oder du schätzt:**

**Leicht (`simple`)**:
- Scope ist klar definiert
- < 5 Files betroffen
- 1-2 Claude Code Sessions
- Keine Feasibility-Prüfung nötig

**Komplex (`complex`)**:
- Scope ist unklar oder groß
- Multiple Komponenten betroffen
- Braucht Zerlegung in Teilaufgaben
- Feasibility-Prüfung sinnvoll

---

## Beispiel-Dialoge

### Beispiel 1: Internes, leichtes Feature

```
User: "Ich brauche ein neues ADR Tool das Markdown validiert"

Consultant: "Das klingt nach einem internen HELIX Feature. Lass mich verstehen:
- Du willst ein Tool in src/helix/tools/ erstellen
- Es soll Markdown-Dateien auf Struktur prüfen
- Ist das korrekt?

Das ist ein klar definiertes Feature. Ich würde den `intern-simple`
Workflow empfehlen:
1. Planning & ADR erstellen
2. Tool implementieren
3. Tests schreiben
4. Dokumentation
5. Deploy to Test
6. E2E Tests
7. Deploy to Prod

Soll ich das Projekt starten?"
```

### Beispiel 2: Internes, komplexes Feature

```
User: "Wir brauchen ein komplett neues Modul für die RAG Integration"

Consultant: "RAG Integration ist ein größeres Vorhaben. Ich habe Fragen:
- Welche RAG-Datenbank (Qdrant, Weaviate, ...)?
- Welche Dokumente werden indexiert?
- Wie wird die Suche getriggert?

Das klingt nach einem komplexen Feature. Ich empfehle `intern-complex`:
1. Feasibility Check (optional)
2. Planning Agent → Zerlegung in 1-5 Teilaufgaben
3. Dynamische Entwicklungsphasen
4. Umfassende Tests
5. Vollständige Dokumentation
6. Deploy & E2E

Magst du mir zuerst mehr Details geben?"
```

### Beispiel 3: Externes Projekt

```
User: "Bau mir ein CLI Tool das CSV Dateien in JSON konvertiert"

Consultant: "Das ist ein eigenständiges Tool, nicht Teil von HELIX selbst.
Ich würde `extern-simple` verwenden:
1. Spezifikation erstellen
2. CLI implementieren
3. Tests (optional)
4. README schreiben

Das Projekt landet in projects/external/csv-to-json/.
Kein Deploy-Zyklus nötig da es nicht in HELIX integriert wird.

Soll ich starten?"
```

---

## Workflow starten

### Schritt 1: Projekt-Verzeichnis

```bash
# Internes Projekt
mkdir -p projects/internal/{projekt-name}/phases

# Externes Projekt
mkdir -p projects/external/{projekt-name}/phases
```

### Schritt 2: Template kopieren

```bash
# Wähle das passende Template
cp templates/workflows/intern-simple.yaml \
   projects/internal/{projekt-name}/phases.yaml

# Oder für komplexe Projekte
cp templates/workflows/intern-complex.yaml \
   projects/internal/{projekt-name}/phases.yaml
```

### Schritt 3: phases.yaml anpassen (optional)

Falls nötig, passe die Phasen an:
- Ändere Beschreibungen
- Füge Input-Files hinzu
- Passe Output-Erwartungen an

### Schritt 4: Via API starten

```bash
# Projekt ausführen
curl -X POST http://localhost:8001/helix/execute \
  -H "Content-Type: application/json" \
  -d '{
    "project_path": "projects/internal/{projekt-name}/",
    "phase_filter": null
  }'

# Antwort:
# {"job_id": "abc123", "status": "running", ...}
```

### Schritt 5: Status überwachen

```bash
# Alle Jobs anzeigen
curl http://localhost:8001/helix/jobs

# Spezifischer Job
curl http://localhost:8001/helix/jobs/{job_id}

# SSE Stream für Echtzeit-Updates
curl http://localhost:8001/helix/stream/{job_id}
```

---

## Troubleshooting

### Phase schlägt fehl

```bash
# 1. Prüfe den Job-Status
curl http://localhost:8001/helix/jobs/{job_id}

# 2. Schau in die Phase-Logs
cat projects/.../phases/{N}/output/logs.txt

# 3. Phase zurücksetzen und neu starten
curl -X POST http://localhost:8001/helix/execute \
  -d '{"project_path": "...", "phase_filter": "N", "reset": true}'
```

### Sub-Agent Verifikation schlägt fehl

Bei `verify_agent: true` Phasen wird der Output von einem Sub-Agent geprüft.
Nach 3 Fehlversuchen (max_retries: 3) wird abgebrochen.

**Lösung:**
1. Prüfe das Feedback im Log
2. Behebe das Problem manuell
3. Phase neu starten mit reset: true

### API nicht erreichbar

```bash
# Prüfe ob der API Server läuft
curl http://localhost:8001/health

# Falls nicht, starte ihn
cd /home/aiuser01/helix-v4
PYTHONPATH=src python3 -m helix.api.main
```

---

## API Endpoints Referenz

| Endpoint | Methode | Beschreibung |
|----------|---------|--------------|
| `/helix/execute` | POST | Projekt starten |
| `/helix/jobs` | GET | Alle Jobs auflisten |
| `/helix/jobs/{id}` | GET | Job-Status abfragen |
| `/helix/jobs/{id}` | DELETE | Job abbrechen |
| `/helix/stream/{id}` | GET | SSE Stream für Echtzeit-Updates |
| `/helix/discuss` | POST | Consultant-Diskussion (TODO) |

---

## Quick Reference

```bash
# Internes Feature (einfach)
mkdir -p projects/internal/mein-feature/phases
cp templates/workflows/intern-simple.yaml projects/internal/mein-feature/phases.yaml
curl -X POST http://localhost:8001/helix/execute -d '{"project_path": "projects/internal/mein-feature/"}'

# Internes Feature (komplex)
mkdir -p projects/internal/grosses-feature/phases
cp templates/workflows/intern-complex.yaml projects/internal/grosses-feature/phases.yaml
curl -X POST http://localhost:8001/helix/execute -d '{"project_path": "projects/internal/grosses-feature/"}'

# Externes Tool
mkdir -p projects/external/mein-tool/phases
cp templates/workflows/extern-simple.yaml projects/external/mein-tool/phases.yaml
curl -X POST http://localhost:8001/helix/execute -d '{"project_path": "projects/external/mein-tool/"}'
```

---

*Erstellt: 2025-12-26*
*Basierend auf: ADR-023, ADR-024*
