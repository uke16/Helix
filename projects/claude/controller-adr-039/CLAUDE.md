# Controller für ADR-039: Code Quality Hardening

Du bist der **Controller** für ADR-039. Deine Aufgabe ist es, den ADR vollständig zu implementieren UND zu verifizieren dass die Integration funktioniert.

## ADR-039 Übersicht

**Ziel:** Hardcoded Paths eliminieren, LSP aktivieren, Dokumentation vervollständigen

### Phase 1: PathConfig Erweitern
- [ ] `src/helix/config/paths.py` erweitern um:
  - DOMAIN_EXPERTS_CONFIG
  - LLM_PROVIDERS_CONFIG  
  - SKILLS_DIR
  - TEMPLATES_DIR
  - TEMPLATES_PHASES

### Phase 2: Module Migrieren (12 Dateien)
- [ ] expert_manager.py → PathConfig().DOMAIN_EXPERTS_CONFIG
- [ ] llm_client.py → PathConfig().LLM_PROVIDERS_CONFIG
- [ ] template_engine.py → PathConfig().TEMPLATES_DIR
- [ ] phase_loader.py → PathConfig().TEMPLATES_PHASES
- [ ] context_manager.py → PathConfig().SKILLS_DIR
- [ ] openai.py → PathConfig().HELIX_ROOT
- [ ] claude_runner.py → PathConfig
- [ ] main.py → sys.path.insert entfernen
- [ ] deployer.py → PathConfig
- [ ] integrator.py → PathConfig
- [ ] validator.py → PathConfig
- [ ] project.py → PathConfig

### Phase 3: LSP Aktivieren
- [ ] ENABLE_LSP_TOOL=1 in config/env.sh
- [ ] pyright in pyproject.toml dev dependencies
- [ ] Verifizieren: `pyright --version`

### Phase 4: Dokumentation
- [ ] docs/CONFIGURATION-GUIDE.md erstellen
- [ ] docs/PATHS.md erstellen
- [ ] ConsultantMeeting in ARCHITECTURE-MODULES.md dokumentieren

### Phase 5: Verifikation
- [ ] `grep -r "/home/aiuser01" src/` findet NICHTS
- [ ] `grep -r "sys.path.insert" src/` findet NICHTS
- [ ] Unit Tests: `pytest tests/unit/ -v`
- [ ] **INTEGRATION TEST** (siehe unten)

---

## 🔴 KRITISCH: Integration Test

**NACH allen Änderungen MUSS dieser Test laufen:**

```bash
# 1. API neu starten
pkill -f "uvicorn.*helix.api" 2>/dev/null
sleep 2
cd /home/aiuser01/helix-v4
export PYTHONPATH="$PWD/src"
nohup python3 -m uvicorn helix.api.main:app --host 0.0.0.0 --port 8001 > /tmp/helix-api.log 2>&1 &
sleep 5

# 2. Consultant Integration Test
curl -X POST http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-OpenWebUI-Chat-Id: integration-test-$(date +%s)" \
  -d '{
    "model": "helix-consultant",
    "messages": [{"role": "user", "content": "Erstelle ein Mini-ADR für einen Bubblesort Algorithmus. Nur 3 Sätze, kein vollständiges ADR nötig."}],
    "stream": false
  }' 2>&1 | head -50

# 3. Prüfe Response
# - Enthält Response Text? → ✅ Integration funktioniert
# - Nur "<!-- STEP: done -->"? → ❌ Streaming Bug
# - 500 Error? → ❌ API crasht
# - Timeout? → ❌ Claude hängt
```

**Wenn der Integration Test fehlschlägt:**
1. Prüfe `/tmp/helix-api.log` für Errors
2. Dokumentiere in BUGS_AND_IMPROVEMENTS.md
3. Fixe das Problem
4. Wiederhole Test

---

## Arbeitsweise

1. **Lies zuerst** das ADR: `adr/039-code-quality-hardening---paths-lsp-documentation.md`
2. **Arbeite Phase für Phase** - nicht alles auf einmal
3. **Nach jeder Phase:** `pytest tests/unit/ -v`
4. **Am Ende:** Integration Test (oben)
5. **Dokumentiere** alle Probleme in `BUGS_AND_IMPROVEMENTS.md`

---

## Completion Criteria

Du bist **FERTIG** wenn:
- [ ] Alle Phasen abgehakt
- [ ] `grep -r "/home/aiuser01" src/` = leer
- [ ] Unit Tests grün
- [ ] **Integration Test erfolgreich** (Consultant antwortet mit Text, nicht nur STEP-Marker)
- [ ] Git commit mit sinnvoller Message

---

## Files

- `status.md` - Dein Fortschritt
- `BUGS_AND_IMPROVEMENTS.md` - Probleme die du findest
- `MANUAL_INTERVENTIONS.md` - Was du manuell fixen musstest
