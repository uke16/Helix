# Phase 14: Self-Evolution System

## Ziel

Implementiere das **HELIX Self-Evolution System** - die Fähigkeit von HELIX, sich selbst sicher weiterzuentwickeln.

## Kontext

- Phase 13 hat den Consultant als Claude Code Instanz implementiert
- Das EVOLUTION-CONCEPT.md definiert die Architektur
- helix-v3-test wurde decommissioned, Ports sind frei
- GitLab Repo ist eingerichtet

## Referenz-Dokumente

**MUST READ:**
- `docs/EVOLUTION-CONCEPT.md` - Das vollständige Konzept
- `docs/ARCHITECTURE-MODULES.md` - Bestehende Modul-Struktur

## Implementierungsplan

Das Self-Evolution System wird in **6 Sub-Phasen** implementiert:

---

### Sub-Phase 14.1: helix-control.sh

**Ziel:** Control Script für HELIX v4 (wie bei v3)

**Datei:** `control/helix-control.sh`

**Befehle:**
```bash
./control/helix-control.sh status      # Status aller Komponenten
./control/helix-control.sh start       # API starten
./control/helix-control.sh stop        # API stoppen
./control/helix-control.sh restart     # API neustarten
./control/helix-control.sh logs        # Logs anzeigen
./control/helix-control.sh docker-up   # Docker Container starten
./control/helix-control.sh docker-down # Docker Container stoppen
./control/helix-control.sh health      # Health Check
```

**Output:**
- `output/14.1/helix-control.sh`

**Quality Gate:** Script ausführbar, `status` funktioniert

---

### Sub-Phase 14.2: helix-v4-test Setup

**Ziel:** Test-System als separates Verzeichnis aufsetzen

**Schritte:**
1. Clone helix-v4 nach helix-v4-test
2. Docker-Compose für Test-Ports erstellen
3. .env.test mit Test-Konfiguration
4. Control Script für Test-System

**Verzeichnis:** `/home/aiuser01/helix-v4-test/`

**Docker Ports (Test):**
| Service | Production | Test |
|---------|-----------|------|
| HELIX API | 8001 | 9001 |
| PostgreSQL | 5432 | 5433 |
| Neo4j HTTP | 7474 | 7475 |
| Neo4j Bolt | 7687 | 7688 |
| Qdrant HTTP | 6333 | 6335 |
| Redis | 6379 | 6380 |

**Output:**
- `output/14.2/docker-compose.test.yaml`
- `output/14.2/.env.test`
- `output/14.2/setup-test-system.sh`

**Quality Gate:** Test-System startet, Health Check OK

---

### Sub-Phase 14.3: Evolution Project Manager

**Ziel:** Modul zur Verwaltung von Evolution-Projekten

**Datei:** `src/helix/evolution/project.py`

**Funktionen:**
```python
class EvolutionProject:
    def create(name: str, spec: dict) -> EvolutionProject
    def get_status() -> str  # pending/developing/ready/deployed/integrated
    def set_status(status: str)
    def get_path() -> Path
    def list_new_files() -> list[Path]
    def list_modified_files() -> list[Path]
    
class EvolutionProjectManager:
    def list_projects() -> list[EvolutionProject]
    def get_project(name: str) -> EvolutionProject
    def create_project(name: str, spec_yaml: str, phases_yaml: str) -> EvolutionProject
    def delete_project(name: str)
```

**Output:**
- `output/14.3/project.py`
- `output/14.3/test_project.py`

**Quality Gate:** Unit Tests bestehen

---

### Sub-Phase 14.4: Deployer & Validator

**Ziel:** Module für Deploy ins Test-System und Validation

**Dateien:**
- `src/helix/evolution/deployer.py`
- `src/helix/evolution/validator.py`

**Deployer Funktionen:**
```python
class Deployer:
    def pre_deploy_sync()      # Git sync helix-v4-test
    def deploy(project: EvolutionProject)  # Copy files
    def restart_test_system()  # Restart API
    def rollback()             # Reset test system
```

**Validator Funktionen:**
```python
class Validator:
    def syntax_check(project: EvolutionProject) -> ValidationResult
    def run_unit_tests() -> ValidationResult
    def run_e2e_tests() -> ValidationResult
    def full_validation() -> ValidationResult
```

**Output:**
- `output/14.4/deployer.py`
- `output/14.4/validator.py`
- `output/14.4/test_deployer.py`
- `output/14.4/test_validator.py`

**Quality Gate:** Unit Tests bestehen

---

### Sub-Phase 14.5: Integrator & RAG Sync

**Ziel:** Integration in Production und RAG-Datenbank Sync

**Dateien:**
- `src/helix/evolution/integrator.py`
- `src/helix/evolution/rag_sync.py`

**Integrator Funktionen:**
```python
class Integrator:
    def pre_integration_backup()  # Git tag/stash
    def integrate(project: EvolutionProject)  # Copy to main
    def post_integration_restart()  # Restart production
    def rollback()  # Git reset
```

**RAG Sync Funktionen:**
```python
class RAGSync:
    def sync_qdrant_to_test()  # Copy embeddings
    def get_sync_status() -> dict
```

**Output:**
- `output/14.5/integrator.py`
- `output/14.5/rag_sync.py`
- `output/14.5/test_integrator.py`

**Quality Gate:** Unit Tests bestehen

---

### Sub-Phase 14.6: API Endpoints & Consultant Update

**Ziel:** REST API für Evolution und Consultant-Awareness

**API Endpoints:**
```
GET  /helix/evolution/projects           # Liste Projekte
GET  /helix/evolution/projects/{name}    # Projekt Status
POST /helix/evolution/projects/{name}/deploy    # Deploy
POST /helix/evolution/projects/{name}/validate  # Validate
POST /helix/evolution/projects/{name}/integrate # Integrate
POST /helix/evolution/projects/{name}/rollback  # Rollback
POST /helix/evolution/sync-rag          # RAG Sync
```

**Consultant Update:**
- Template erweitern für Evolution-Projekte
- Consultant kann "type: evolution" Projekte erstellen
- Consultant kennt Evolution-Workflow

**Output:**
- `output/14.6/routes_evolution.py`
- `output/14.6/consultant_evolution.md.j2` (Template Update)
- `output/14.6/test_routes_evolution.py`

**Quality Gate:** API Endpoints funktionieren, E2E Test

---

## Gesamtstruktur nach Phase 14

```
helix-v4/
├── control/
│   └── helix-control.sh          # NEU
├── src/helix/
│   ├── evolution/                 # NEU
│   │   ├── __init__.py
│   │   ├── project.py
│   │   ├── deployer.py
│   │   ├── validator.py
│   │   ├── integrator.py
│   │   └── rag_sync.py
│   └── api/routes/
│       └── evolution.py          # NEU
├── docker/
│   ├── production/               # Umbenennen von docker/
│   └── test/                     # NEU
│       └── docker-compose.yaml
└── templates/consultant/
    └── session.md.j2             # UPDATE

helix-v4-test/                     # NEU (separates Verzeichnis)
├── src/helix/
├── docker/
├── control/
│   └── helix-control.sh
└── .env.test
```

---

## Dokumentation Updates

Nach Implementation aktualisieren:
- [ ] `docs/EVOLUTION-CONCEPT.md` - Status auf IMPLEMENTED
- [ ] `docs/ARCHITECTURE-MODULES.md` - evolution/ Package hinzufügen
- [ ] `ONBOARDING.md` - Evolution-Workflow beschreiben
- [ ] `CLAUDE.md` - Evolution-Projekttyp dokumentieren
- [ ] `README.md` - Self-Evolution Feature erwähnen

---

## Abhängigkeiten

```
14.1 (control.sh)
    ↓
14.2 (test setup) ←── benötigt control.sh
    ↓
14.3 (project manager)
    ↓
14.4 (deployer/validator) ←── benötigt 14.2 + 14.3
    ↓
14.5 (integrator/rag) ←── benötigt 14.4
    ↓
14.6 (API/consultant) ←── benötigt alle vorherigen
```

---

## Geschätzter Aufwand

| Sub-Phase | Dateien | Zeilen (geschätzt) |
|-----------|---------|-------------------|
| 14.1 | 1 | ~200 |
| 14.2 | 3 | ~300 |
| 14.3 | 2 | ~250 |
| 14.4 | 4 | ~400 |
| 14.5 | 3 | ~300 |
| 14.6 | 3 | ~350 |
| **Total** | **16** | **~1,800** |

---

## Quality Gate für Phase 14

- [ ] helix-control.sh funktioniert (status, start, stop)
- [ ] helix-v4-test System läuft auf Test-Ports
- [ ] Evolution-Projekt kann erstellt werden
- [ ] Deploy ins Test-System funktioniert
- [ ] Validation läuft (syntax, tests)
- [ ] Integration in Main funktioniert
- [ ] RAG Sync funktioniert
- [ ] API Endpoints erreichbar
- [ ] Consultant kann Evolution-Projekte erstellen
- [ ] Dokumentation aktualisiert
