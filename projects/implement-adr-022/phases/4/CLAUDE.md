# Phase 4: Aufräumen - Toter Code löschen

## Deine Aufgabe

Lösche den toten Code NACHDEM alles via API funktioniert.

## ⚠️ WICHTIG: Erst prüfen, dann löschen!

Bevor du etwas löschst, stelle sicher:

```bash
# 1. API funktioniert
curl http://localhost:8001/

# 2. CLI funktioniert via API
./scripts/helix run projects/test-simple --dry-run

# 3. Keine Imports mehr auf alte Dateien
grep -r "orchestrator_legacy" src/helix/
grep -r "from helix.orchestrator import" src/helix/
# Sollte NICHTS finden (außer in orchestrator/ selbst)
```

## Was du tun musst

### 1. Backup erstellen

```bash
mkdir -p output/backup/orchestrator
cp src/helix/orchestrator_legacy.py output/backup/
cp -r src/helix/orchestrator/* output/backup/orchestrator/
```

### 2. Dateien löschen

```bash
rm src/helix/orchestrator_legacy.py
rm -rf src/helix/orchestrator/
```

### 3. Imports fixen

Suche und fixe alle Imports die auf gelöschte Dateien verweisen:

```bash
# Finde alle Imports
grep -r "orchestrator_legacy\|from helix.orchestrator" src/ tests/

# Fixe sie - sie sollten jetzt auf helix.api.orchestrator zeigen:
# VORHER: from helix.orchestrator import Orchestrator
# NACHHER: from helix.api.orchestrator import UnifiedOrchestrator
```

### 4. Dokumentiere was gelöscht wurde

Erstelle `output/DELETED_FILES.md`:

```markdown
# Gelöschte Dateien

## orchestrator_legacy.py (417 Zeilen)
- War: CLI Orchestrator
- Ersetzt durch: src/helix/api/orchestrator.py

## orchestrator/ package (~2000 Zeilen)
- orchestrator/__init__.py
- orchestrator/runner.py
- orchestrator/phase_executor.py
- orchestrator/data_flow.py
- orchestrator/status.py
- War: ADR-017 Design (nie genutzt)
- Ersetzt durch: src/helix/api/orchestrator.py

## Total: ~2400 Zeilen entfernt
```

## Erfolgskriterien

```bash
# 1. Alte Dateien sind weg
ls src/helix/orchestrator_legacy.py 2>&1 | grep "No such file"
ls src/helix/orchestrator/ 2>&1 | grep "No such file"

# 2. Backup existiert
ls output/backup/orchestrator_legacy.py
ls output/backup/orchestrator/

# 3. Keine Import Errors
cd /home/aiuser01/helix-v4
PYTHONPATH=src python3 -c "from helix.api.orchestrator import UnifiedOrchestrator; print('OK')"
PYTHONPATH=src python3 -c "import helix; print('OK')"

# 4. Tests laufen noch
PYTHONPATH=src pytest tests/ -v --ignore=tests/orchestrator/
```

## Checkliste

- [ ] Backup von orchestrator_legacy.py erstellt
- [ ] Backup von orchestrator/ erstellt
- [ ] orchestrator_legacy.py gelöscht
- [ ] orchestrator/ package gelöscht
- [ ] Alle Imports gefixed
- [ ] Keine ImportError
- [ ] Tests laufen noch
- [ ] DELETED_FILES.md erstellt
