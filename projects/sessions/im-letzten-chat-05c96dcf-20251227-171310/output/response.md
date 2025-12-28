# Antwort: Evolution Workflow und Testsystem

## Deine Frage

> Wird der Evolution Workflow ein deploy von den neuen Daten machen und vorher auf die gleiche Version gut gehen wie das Production System?

## Antwort: Ja, genau so funktioniert es.

Der Evolution Workflow ist so designed:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         EVOLUTION WORKFLOW                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. GIT SYNC                                                                 │
│     └─> Testsystem wird auf gleiche Git-Version gebracht wie Production     │
│     └─> `sync_git_version: true` in phases.yaml                             │
│                                                                              │
│  2. DEPLOY                                                                   │
│     └─> Modifizierte Dateien werden ins Testsystem kopiert                  │
│     └─> API wird im Testsystem neu gestartet                                │
│                                                                              │
│  3. VALIDATE                                                                 │
│     └─> Syntax-Check                                                         │
│     └─> Unit Tests                                                           │
│     └─> E2E Tests                                                            │
│                                                                              │
│  4. INTEGRATE (nur wenn Validation OK)                                       │
│     └─> Kopiere in Production                                                │
│     └─> Neustart Production API                                              │
│                                                                              │
│  5. ROLLBACK (bei Fehler)                                                    │
│     └─> Automatisch wenn Tests fehlschlagen                                  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Sicherheitsgarantien

| Garantie | Beschreibung |
|----------|--------------|
| Git-Sync | Testsystem hat exakt gleiche Version wie Production |
| Isolation | Änderungen werden zuerst isoliert getestet |
| Validierung | Syntax, Unit, E2E Tests vor Integration |
| Rollback | Automatisch bei Fehler |

---

## Was ich jetzt vorbereitet habe

Ich habe die Spezifikation für den Bugfix erstellt:

### 1. ADR-027: Stale Response Bugfix

Dokumentiert die 3 Bugs und deren Fixes:
- Bug 1: Alte `response.md` vor Start löschen
- Bug 2: Timestamp-Validierung
- Bug 3: Explizite Fehlermeldung bei Timeout/Error

### 2. phases.yaml: 3-Phasen Workflow

```
Phase 1: Implementation & Test
    └─> Fix implementieren in openai.py

Phase 2: Deploy & Validate
    └─> Deploy zum Testsystem
    └─> Testsystem hat gleiche Git-Version wie Production
    └─> API Neustart
    └─> Validierung

Phase 3: Integration
    └─> Nur wenn Tests bestanden
    └─> Kopie in Production
    └─> Production API Neustart
```

---

## Nächster Schritt

Sag **"Starte!"** und ich führe den Workflow aus:

1. Implementiere den Fix
2. Deploye zum Testsystem (mit Git-Sync)
3. Validiere
4. Integriere in Production (wenn Tests OK)

Alternativ kann ich auch nur Phase 1 (Implementation) machen und du validierst manuell.

---

*Session: im-letzten-chat-05c96dcf-20251227-171310*
