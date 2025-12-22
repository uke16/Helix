# HELIX v4 Self-Evolution System - Konzept

> **Status:** IMPLEMENTED - Phase 14 Complete
> **Erstellt:** 2024-12-21
> **Ziel:** HELIX kann sich selbst sicher weiterentwickeln

---

## 1. Übersicht

### Das Problem

HELIX v4 soll sich selbst weiterentwickeln können. Das ist gefährlich:
- Claude Code könnte eigene Dateien überschreiben
- Syntax-Fehler könnten das System unbrauchbar machen
- Keine Möglichkeit zum Testen vor Integration

### Die Lösung

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   helix-v4/ (PRODUCTION)           helix-v4-test/ (TEST)                   │
│   ══════════════════════           ══════════════════════                   │
│                                                                             │
│   • Consultant läuft hier          • Komplett unabhängiges System           │
│   • API auf Port 8001              • API auf Port 9001                      │
│   • Production Datenbanken         • Isolierte Test-Datenbanken             │
│   • Wird NIE direkt modifiziert    • Hier wird deployed & getestet          │
│                                                                             │
│   projects/evolution/              (Sync von helix-v4 bei Deploy)           │
│   └── feature-xyz/                                                          │
│       ├── new/        ─────────────────────────────────────────►            │
│       └── modified/   ─────────────────────────────────────────►            │
│                                                                             │
│                       ◄──────────── Wenn Tests OK ────────────►             │
│                       Integration zurück in helix-v4                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Kernprinzip: Zettel statt Telefon

Claude Code Instanzen sind **kurzlebig**. Sie starten, arbeiten, beenden sich.
Es gibt **keinen Dialog** zwischen laufenden Instanzen.

**Kommunikation funktioniert über Dateien:**

```
Consultant                     Dateisystem                    Developer
    │                              │                              │
    │  Schreibt spec.yaml          │                              │
    ├─────────────────────────────►│                              │
    │                              │                              │
    💀 (beendet sich)              │                              │
                                   │                              │
                                   │  Developer wird gestartet    │
                                   │◄─────────────────────────────┤
                                   │                              │
                                   │  Liest spec.yaml             │
                                   │◄─────────────────────────────┤
                                   │                              │
                                   │  Schreibt Code               │
                                   │◄─────────────────────────────┤
                                   │                              │
                                   │  Schreibt status.json        │
                                   │◄─────────────────────────────┤
                                   │                              │
                                   │                    💀 (beendet sich)
```

---

## 3. Systemarchitektur

### 3.1 Zwei unabhängige Systeme

| Aspekt | helix-v4 (PRODUCTION) | helix-v4-test (TEST) |
|--------|----------------------|---------------------|
| **Zweck** | Produktives System | Testen vor Integration |
| **HELIX API** | Port 8001 | Port 9001 |
| **PostgreSQL** | Port 5432 | Port 5433 |
| **Neo4j HTTP** | Port 7474 | Port 7475 |
| **Neo4j Bolt** | Port 7687 | Port 7688 |
| **Qdrant HTTP** | Port 6333 | Port 6335 |
| **Qdrant gRPC** | Port 6334 | Port 6336 |
| **Redis** | Port 6379 | Port 6380 |
| **Läuft** | Immer | Immer (parallel) |

### 3.2 Verzeichnisstruktur

```
/home/aiuser01/
│
├── helix-v4/                          # PRODUCTION SYSTEM
│   ├── src/helix/                     # Production Code
│   ├── config/
│   ├── docker/
│   │   ├── production/                # docker-compose.yaml
│   │   └── test/                      # docker-compose.test.yaml (Referenz)
│   ├── control/
│   │   └── helix-control.sh           # NEU: Control Script
│   │
│   └── projects/
│       ├── sessions/                  # Consultant Sessions
│       ├── external/                  # Externe Projekte
│       └── evolution/                 # HELIX Self-Evolution Projekte
│           └── feature-xyz/
│               ├── spec.yaml
│               ├── phases.yaml
│               ├── status.json        # pending/developing/ready/deployed/integrated
│               ├── new/               # Neue Dateien (gespiegelte Struktur)
│               │   └── src/helix/
│               │       └── evolution/
│               │           └── new_module.py
│               └── modified/          # Modifizierte Dateien (Kopien)
│                   └── src/helix/
│                       └── orchestrator.py
│
└── helix-v4-test/                     # TEST SYSTEM
    ├── src/helix/                     # Wird bei Deploy überschrieben
    ├── config/
    ├── docker/
    │   └── docker-compose.yaml        # Test-Ports
    └── control/
        └── helix-control.sh           # Control Script für Test
```

### 3.3 Port-Übersicht

```
PRODUCTION (helix-v4)          TEST (helix-v4-test)
─────────────────────          ─────────────────────
8001  HELIX API                9001  HELIX API
5432  PostgreSQL               5433  PostgreSQL
7474  Neo4j HTTP               7475  Neo4j HTTP
7687  Neo4j Bolt               7688  Neo4j Bolt
6333  Qdrant HTTP              6335  Qdrant HTTP
6334  Qdrant gRPC              6336  Qdrant gRPC
6379  Redis                    6380  Redis
```

---

## 4. Workflow

### 4.1 Evolution-Projekt Lifecycle

```
┌─────────────┐
│   PENDING   │  User + Consultant besprechen Feature
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ DEVELOPING  │  Developer-Phasen laufen (new/ und modified/ werden gefüllt)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│    READY    │  Entwicklung abgeschlossen, bereit für Deploy
└──────┬──────┘
       │ User sagt: "Deploy!"
       ▼
┌─────────────┐
│  DEPLOYED   │  Code ist im Test-System, Tests laufen
└──────┬──────┘
       │
       ├───────────────┐
       │               │
       ▼               ▼
┌─────────────┐  ┌─────────────┐
│ INTEGRATED  │  │   FAILED    │  Tests bestanden / fehlgeschlagen
└─────────────┘  └─────────────┘
```

### 4.2 Detaillierter Ablauf

#### Phase 1: Entwicklung (in helix-v4)

1. **User startet Chat** in Open WebUI mit Consultant
2. **Consultant erstellt** `projects/evolution/feature-xyz/`
   - spec.yaml
   - phases.yaml
   - status.json: `{"status": "pending"}`
3. **Developer-Phasen** laufen (Claude Code Instanzen)
   - Neue Dateien → `new/src/helix/...`
   - Modifikationen:
     - Liest Original aus `../../src/helix/...`
     - Kopiert nach `modified/src/helix/...`
     - Modifiziert die Kopie
4. **Nach letzter Phase**: status.json → `{"status": "ready"}`

#### Phase 2: Deploy (in helix-v4-test)

1. **User sagt**: "Deploy Feature XYZ!"
2. **System prüft**: Nur ein Deploy gleichzeitig möglich
3. **Pre-Deploy**:
   ```bash
   cd /home/aiuser01/helix-v4-test
   git fetch origin
   git reset --hard origin/main  # Gleiche Version wie Production
   ```
4. **Deploy**:
   ```bash
   # Neue Dateien kopieren
   cp -r /home/aiuser01/helix-v4/projects/evolution/feature-xyz/new/* .
   
   # Modifizierte Dateien kopieren
   cp -r /home/aiuser01/helix-v4/projects/evolution/feature-xyz/modified/* .
   ```
5. **Restart**:
   ```bash
   ./control/helix-control.sh restart
   ```
6. **Status**: status.json → `{"status": "deployed"}`

#### Phase 3: Validation

1. **Syntax Check**: `python -m py_compile` auf alle .py Dateien
2. **Unit Tests**: `pytest tests/`
3. **E2E Tests**: Gegen Test-API (Port 9001)
4. **Optional**: Benchmark Main vs Test

#### Phase 4a: Integration (bei Erfolg)

1. **User sagt**: "Integriere!"
2. **In helix-v4**:
   ```bash
   cp -r projects/evolution/feature-xyz/new/* .
   cp -r projects/evolution/feature-xyz/modified/* .
   git add -A
   git commit -m "Feature: XYZ"
   ```
3. **Restart Production**:
   ```bash
   ./control/helix-control.sh restart
   ```
4. **Status**: status.json → `{"status": "integrated"}`
5. **Cleanup**: Evolution-Projekt archivieren/löschen

#### Phase 4b: Rollback (bei Fehler)

1. **Status**: status.json → `{"status": "failed", "error": "..."}`
2. **Test-System zurücksetzen**:
   ```bash
   cd /home/aiuser01/helix-v4-test
   git reset --hard origin/main
   ./control/helix-control.sh restart
   ```
3. **User informieren**: Fehler anzeigen
4. **Optional**: Neuer Entwicklungsversuch mit Hints

---

## 5. Entscheidungen

### 5.1 Mehrere Evolution-Projekte parallel

**Entscheidung**: JA, mehrere Projekte können parallel entwickelt werden.

```
projects/evolution/
├── feature-a/   ← In Entwicklung (status: developing)
├── feature-b/   ← In Entwicklung (status: developing)
└── feature-c/   ← Bereit (status: ready)
```

**Aber**: Nur EIN Projekt kann gleichzeitig deployed werden (ein Test-System).

**Konflikt-Handling**:
- Wenn beide dieselbe Datei modifizieren → Warnung beim Deploy
- User muss entscheiden welches zuerst
- Nach Integration des ersten → zweites muss neu-gemergt werden

### 5.2 Test-Datenbanken

**Entscheidung**: RAG-Datenbanken werden 1:1 kopiert.

- **Qdrant (Embeddings)**: Vollständige Kopie von Production
  - Enthält alle Embeddings für Skills, Dokumentation, etc.
  - Ermöglicht realistische RAG-Tests
  
- **PostgreSQL**: Struktur + Seeds (keine User-Daten)
  
- **Neo4j**: Struktur + Seeds

**Warum RAG kopieren?**
- RAG-Suche muss realistisch funktionieren
- Embeddings sind nicht sensibel (keine Personendaten)
- Neu-Embedden würde lange dauern und API-Kosten verursachen

**Sync-Strategie**:
```bash
# Bei Pre-Deploy: RAG-Daten synchronisieren
./control/helix-control.sh sync-rag-to-test
```

### 5.3 Fehlerbehandlung

**Entscheidung**: Fehler melden, User entscheidet.

Bei fehlgeschlagenen Tests:
1. Detaillierter Fehlerbericht in status.json
2. User wird informiert (im Chat)
3. User kann:
   - Neu entwickeln lassen (mit Hints)
   - Manuell fixen
   - Abbrechen

### 5.4 Rollback-Strategie

**Entscheidung**: Git-basiertes Rollback.

- Vor Integration: `git stash` oder Tag erstellen
- Bei Fehler: `git reset --hard` oder `git stash pop`
- Container: Restart reicht (Code ändert sich, nicht DB)

---

## 6. helix-control.sh

Neues Control-Script für HELIX v4:

```bash
./control/helix-control.sh status     # Status anzeigen
./control/helix-control.sh start      # API starten
./control/helix-control.sh stop       # API stoppen
./control/helix-control.sh restart    # API neustarten
./control/helix-control.sh logs       # Logs anzeigen
./control/helix-control.sh docker-up  # Docker Container starten
./control/helix-control.sh docker-down # Docker Container stoppen
```

---

## 7. Neue Module

| Modul | Zweck |
|-------|-------|
| `src/helix/evolution/__init__.py` | Package |
| `src/helix/evolution/project.py` | Evolution-Projekt Management |
| `src/helix/evolution/deployer.py` | Deploy ins Test-System |
| `src/helix/evolution/validator.py` | Tests und Validation |
| `src/helix/evolution/integrator.py` | Integration in Production |

---

## 8. API Erweiterungen

| Endpoint | Zweck |
|----------|-------|
| `GET /helix/evolution/projects` | Liste aller Evolution-Projekte |
| `GET /helix/evolution/projects/{id}` | Status eines Projekts |
| `POST /helix/evolution/projects/{id}/deploy` | Deploy ins Test-System |
| `POST /helix/evolution/projects/{id}/integrate` | Integration in Production |
| `POST /helix/evolution/projects/{id}/rollback` | Rollback |

---

## 9. Offene Punkte

- [ ] helix-v4-test Verzeichnis initial aufsetzen
- [ ] docker-compose.test.yaml erstellen
- [ ] helix-control.sh implementieren
- [ ] Test-Seeds/Fixtures definieren
- [ ] RAG Test-Collection erstellen

---

## 10. Nächste Schritte

1. ✅ Konzept dokumentieren (dieses Dokument)
2. [ ] Review durch User
3. [ ] helix-control.sh für v4 erstellen
4. [ ] helix-v4-test aufsetzen
5. [ ] Evolution-Module implementieren
