# Bugs and Improvements

> Erstelle diese Datei nach Abschluss des Projekts.
> Sammelt alle Erkenntnisse für zukünftige Workflow-Verbesserungen.

---

## Bugs gefunden

(Nach Abschluss ausfüllen)

## Fehlende Features

(Nach Abschluss ausfüllen)

## ADR Unklarheiten

(Nach Abschluss ausfüllen)

## Verbesserungsvorschläge

(Nach Abschluss ausfüllen)

---

## Pre-documented Issues (vor Ausführung bekannt)

### Missing Feature: Evolution Project Creation API

**Problem:** Kein POST /helix/evolution/projects Endpoint
**Impact:** Controller/Consultant kann keine Projekte programmatisch erstellen
**Workaround:** Projekt manuell erstellt
**Vorschlag:** API Endpoint hinzufügen:
```
POST /helix/evolution/projects
{
  "name": "mcp-server-032",
  "adr_path": "adr/032-xxx.md"
}
```
Der Endpoint sollte:
- ADR lesen und validieren
- phases.yaml aus ADR.files generieren
- Projekt-Struktur erstellen
- Optional: Job direkt starten
