# Controller: ADR-035 (Consultant API Hardening - Security & Reliability)

Du supervisest den Evolution Workflow für ADR-035.

## Kontext

ADR-035 konsolidiert 19 Bugs aus Code-Audits, davon 3 kritische Sicherheitslücken.
Es ist ein **FIX-ADR** mit klaren Lösungen - keine architektonischen Entscheidungen nötig.

**ADR**: `/home/aiuser01/helix-v4/adr/035-consultant-api-hardening---security-reliability-fi.md`
**Bug Sources**:
- `/bugs/from-audit-consultant-code.md` (13 neue)
- `/bugs/from-controller-adr-032.md` (5)
- `/bugs/from-controller-adr-034.md` (3)

## Priorität

1. **Phase 1: Security** (KRITISCH - sofort)
   - Random Session IDs (uuid4 statt Hash)
   - Input Validation Middleware
   - Rate Limiting

2. **Phase 2: Reliability** (HOCH)
   - File Locking für Race Conditions
   - Path Traversal Prevention
   - Session Archivierung (Zip, NICHT löschen!)

3. **Phase 3: Code Quality** (MITTEL)
   - Zentrale PathConfig
   - DRY für PATH-Setup

## Workflow

### 1. Skills lesen
```bash
cat /home/aiuser01/helix-v4/skills/helix/SKILL.md
cat /home/aiuser01/helix-v4/skills/helix/evolution/SKILL.md
```

### 2. ADR verstehen
```bash
cat /home/aiuser01/helix-v4/adr/035-consultant-api-hardening---security-reliability-fi.md
```

### 3. Projekt erstellen
```bash
mkdir -p /home/aiuser01/helix-v4/projects/evolution/api-hardening-035
cp /home/aiuser01/helix-v4/adr/035-consultant-api-hardening---security-reliability-fi.md \
   /home/aiuser01/helix-v4/projects/evolution/api-hardening-035/ADR-035.md
```

### 4. Phases erstellen

Basierend auf ADR-035 Implementation Section:

```yaml
# phases.yaml
phases:
  01-security-session-ids:
    description: "Kryptografisch sichere Session-IDs mit uuid4"
    files:
      - src/helix/api/session_manager.py
    tests:
      - tests/api/test_session_security.py
    
  02-security-input-validation:
    description: "Input Validation Middleware"
    files:
      - src/helix/api/middleware/input_validator.py
    tests:
      - tests/api/test_input_validator.py
      
  03-security-rate-limiting:
    description: "Rate Limiting mit slowapi"
    files:
      - src/helix/api/middleware/rate_limiter.py
      - src/helix/api/routes/openai.py
    tests:
      - tests/api/test_rate_limiter.py
      
  04-reliability-file-locking:
    description: "Race Condition Prevention mit filelock"
    files:
      - src/helix/api/session_manager.py
    tests:
      - tests/api/test_session_security.py
      
  05-reliability-path-sanitization:
    description: "Path Traversal Prevention"
    files:
      - src/helix/api/session_manager.py
    tests:
      - tests/api/test_session_security.py
      
  06-reliability-archivierung:
    description: "Session Archivierung (Zip, nichts löschen!)"
    files:
      - src/helix/api/session_manager.py
    tests:
      - tests/api/test_session_cleanup.py
      
  07-code-quality-paths:
    description: "Zentrale PathConfig"
    files:
      - src/helix/config/paths.py
      - src/helix/claude_runner.py
      - src/helix/api/routes/openai.py
```

### 5. Execute & Monitor

```bash
curl -X POST http://localhost:8001/helix/execute \
  -d '{"project_path": "projects/evolution/api-hardening-035"}'
```

### 6. Deploy Pipeline

```bash
curl -X POST http://localhost:8001/helix/evolution/projects/api-hardening-035/deploy
curl -X POST http://localhost:8001/helix/evolution/projects/api-hardening-035/validate
curl -X POST http://localhost:8001/helix/evolution/projects/api-hardening-035/integrate
```

## Neue Dependencies

Vor dem Start sicherstellen:
```bash
cd /home/aiuser01/helix-v4
pip install slowapi filelock --break-system-packages
```

## Bei Problemen

- Dokumentiere JEDEN manuellen Eingriff in `MANUAL_INTERVENTIONS.md`
- Nach Abschluss: `BUGS_AND_IMPROVEMENTS.md` ausfüllen
