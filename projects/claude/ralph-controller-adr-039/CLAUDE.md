# Ralph Controller für ADR-039: Code Quality Hardening

Du bist ein **Ralph Controller** - du arbeitest iterativ bis alles funktioniert.

## WICHTIG: Ralph Loop Regeln

1. Du bekommst denselben Prompt bei jeder Iteration
2. Deine vorherige Arbeit ist in Dateien sichtbar (git history)
3. Lies `status.md` um zu sehen was du schon gemacht hast
4. Arbeite weiter wo du aufgehört hast
5. Wenn ALLES fertig ist: Output `<promise>ADR039_COMPLETE</promise>`

---

## Deine Aufgabe

**ADR:** `../../adr/039-code-quality-hardening---paths-lsp-documentation.md`

### Kern-Ziele von ADR-039

1. **Hardcoded Paths eliminieren** - Keine `/home/aiuser01` mehr im Code
2. **PathConfig erweitern** - Zentrale Pfad-Konfiguration
3. **LSP aktivieren** - pyright Integration
4. **Dokumentation** - PATHS.md, CONFIGURATION-GUIDE.md

---

## Phase 1: PathConfig erweitern

Datei: `src/helix/config/paths.py`

Füge hinzu:
```python
@property
def DOMAIN_EXPERTS_CONFIG(self) -> Path:
    return self.HELIX_ROOT / "config" / "domain-experts.yaml"

@property
def LLM_PROVIDERS_CONFIG(self) -> Path:
    return self.HELIX_ROOT / "config" / "llm-providers.yaml"

@property
def SKILLS_DIR(self) -> Path:
    return self.HELIX_ROOT / "skills"

@property
def TEMPLATES_DIR(self) -> Path:
    return self.HELIX_ROOT / "templates"
```

---

## Phase 2: Module migrieren

Ersetze hardcoded Paths in diesen Dateien:
- `src/helix/consultant/expert_manager.py`
- `src/helix/llm_client.py`
- `src/helix/template_engine.py`
- `src/helix/phase_loader.py`
- `src/helix/context_manager.py`
- `src/helix/api/routes/openai.py`

**Pattern:**
```python
# ALT:
config_path = "/home/aiuser01/helix-v4/config/domain-experts.yaml"

# NEU:
from helix.config.paths import PathConfig
config_path = PathConfig().DOMAIN_EXPERTS_CONFIG
```

---

## Phase 3: Verification Checks

```bash
cd /home/aiuser01/helix-v4

# Check 1: Keine hardcoded Paths mehr
echo "=== Hardcoded Paths Check ==="
grep -r "/home/aiuser01" src/ --include="*.py" | grep -v "__pycache__" | grep -v ".pyc"
# MUSS LEER SEIN!

# Check 2: Unit Tests
echo "=== Unit Tests ==="
export PYTHONPATH="$PWD/src"
python3 -m pytest tests/unit/ -v --tb=short

# Check 3: Syntax Check
echo "=== Syntax Check ==="
python3 -m py_compile src/helix/config/paths.py
python3 -m py_compile src/helix/consultant/expert_manager.py
python3 -m py_compile src/helix/llm_client.py
```

---

## Phase 4: Integration Test (KRITISCH!)

```bash
# API neu starten
pkill -f "uvicorn.*helix.api" 2>/dev/null
sleep 2
cd /home/aiuser01/helix-v4
export PYTHONPATH="$PWD/src"
nohup python3 -m uvicorn helix.api.main:app --host 0.0.0.0 --port 8001 > /tmp/helix-api.log 2>&1 &
sleep 5

# Smoke Test
curl -s -X POST http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-OpenWebUI-Chat-Id: smoke-$(date +%s)" \
  -d '{"model":"helix-consultant","messages":[{"role":"user","content":"Was ist 2+2?"}],"stream":false}' \
  | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
    if len(content) > 20:
        print('✅ INTEGRATION TEST PASSED')
    else:
        print('❌ INTEGRATION TEST FAILED - Response zu kurz')
        sys.exit(1)
except Exception as e:
    print(f'❌ INTEGRATION TEST FAILED - {e}')
    sys.exit(1)
"
```

---

## Phase 5: Completion

Wenn ALLE Checks grün:

1. `status.md` aktualisieren
2. Git commit: `git add -A && git commit --no-verify -m "ADR-039: Code Quality Hardening - Paths consolidated"`
3. Output: `<promise>ADR039_COMPLETE</promise>`

---

## Status Tracking

Aktualisiere `status.md` nach JEDER Aktion:
- Was hast du gemacht?
- Was ist noch offen?
- Welche Fehler sind aufgetreten?

---

## NIEMALS die Promise ausgeben wenn:

- `grep -r "/home/aiuser01" src/` etwas findet
- Unit Tests fehlschlagen
- Integration Test fehlschlägt

Die Promise ist ein VERSPRECHEN dass alles funktioniert!
