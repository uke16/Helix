# Ralph Multi-Phase Pattern

## Problem

Bei ADRs mit mehreren Phasen macht Ralph oft nur die erste Phase und gibt dann das Promise aus.

**Beispiel ADR-039:**
- Phase 1 (Paths): ✅ Fertig
- Phase 2 (LSP): ❌ Vergessen
- Phase 3 (Docs): ❌ Vergessen
- Phase 4 (Verify): ✅ Gemacht

Ralph gab `<promise>ADR039_COMPLETE</promise>` aus obwohl Phase 2+3 fehlten.

## Lösung: Verifikations-Script

**Jedes Multi-Phase ADR braucht ein Verifikations-Script:**

```
control/verify-adr-XXX.sh
```

**Das Script:**
1. Prüft JEDE Phase automatisch
2. Gibt exit 0 nur wenn ALLE Phasen OK
3. Gibt exit 1 wenn mindestens eine Phase fehlt

## CLAUDE.md Template für Multi-Phase Ralph

```markdown
# Ralph Controller für ADR-XXX

## KRITISCH: Vor dem Promise

**DU DARFST `<promise>ADR_XXX_COMPLETE</promise>` NUR AUSGEBEN WENN:**

```bash
./control/verify-adr-XXX.sh
# Exit code MUSS 0 sein!
```

Wenn das Script FAILED → Fixe die fehlenden Phasen → Retry

---

## Phasen

### Phase 1: [Name]
- [ ] Task 1
- [ ] Task 2

### Phase 2: [Name]
- [ ] Task 3
- [ ] Task 4

### Phase N: [Name]
- [ ] Task N

---

## Verifikation

Nach JEDER Phase: Führe `./control/verify-adr-XXX.sh` aus um zu sehen was noch fehlt.

Am Ende: Nur wenn das Script "ALLE PHASEN BESTANDEN" zeigt, darfst du das Promise ausgeben.
```

## Verifikations-Script Template

```bash
#!/bin/bash
# verify-adr-XXX.sh

FAILED=0

echo "▶ Phase 1: [Name]"
if [CHECK_1]; then
    echo "  ✅ Check 1 passed"
else
    echo "  ❌ Check 1 failed"
    FAILED=1
fi

echo "▶ Phase 2: [Name]"
if [CHECK_2]; then
    echo "  ✅ Check 2 passed"
else
    echo "  ❌ Check 2 failed"
    FAILED=1
fi

# ... mehr Phasen ...

if [ "$FAILED" -eq 0 ]; then
    echo "✅ ALLE PHASEN BESTANDEN - Promise erlaubt"
    exit 0
else
    echo "❌ FAILED - Kein Promise!"
    exit 1
fi
```

## Best Practices

### 1. Automatisierbare Checks

```bash
# ✅ GUT: Automatisch prüfbar
if [ -f "docs/README.md" ]; then ...
if grep -q "pyright" pyproject.toml; then ...
if python3 -m pytest tests/ -q; then ...

# ❌ SCHLECHT: Nicht automatisch prüfbar
# "Code ist gut geschrieben" - Wie prüft man das?
```

### 2. Klare Exit Codes

```bash
# Phase failed → exit 1 (nicht exit 0!)
if ! some_check; then
    FAILED=1  # Merken, aber weitermachen
fi

# Am Ende:
exit $FAILED  # 0 = alle OK, 1+ = mindestens einer failed
```

### 3. Informative Ausgabe

```bash
echo "▶ Phase 2: LSP"
echo "  ❌ FAILED: pyright fehlt in pyproject.toml"
echo "  → Füge hinzu: pyright = \"^1.1.0\" unter [tool.poetry.dev-dependencies]"
```

## Workflow

```
Ralph startet
    ↓
Arbeitet an Phase 1
    ↓
Führt verify-script aus → Phase 2+3 fehlen noch
    ↓
Arbeitet an Phase 2
    ↓
Führt verify-script aus → Phase 3 fehlt noch
    ↓
Arbeitet an Phase 3
    ↓
Führt verify-script aus → ALLE BESTANDEN ✅
    ↓
<promise>ADR_XXX_COMPLETE</promise>
```
