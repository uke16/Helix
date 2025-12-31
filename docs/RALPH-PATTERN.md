# Ralph Automation Pattern

## Overview

Ralph ermöglicht iterative ADR-Ausführung mit intelligenter Consultant-Verifikation.

## Kern-Konzepte

### 1. Incremental Goals
Arbeite in kleinen Phasen mit Tests nach jeder Phase:
- Phase 1 → Test → GRÜN → weiter
- Phase 2 → Test → GRÜN → weiter
- FINAL → Consultant Verify → Promise

### 2. Consultant-als-Verify
Der Consultant LIEST das ADR und versteht ALLE Anforderungen:
- Textuelle Requirements ("Default soll 1 sein")
- Implizite Checks (pyright, grep)
- Kontext-Verständnis

### 3. Sub-Agent Spawn
Developer kann Consultant jederzeit nutzen:
```bash
./control/spawn-consultant.sh review src/foo.py
./control/spawn-consultant.sh analyze "Thema"
```

## Quick Start

### Controller erstellen
```bash
mkdir -p projects/claude/controller-adr-XXX
# CLAUDE.md mit Incremental Goals schreiben
```

### Ralph Loop starten
```bash
/ralph-wiggum:ralph-loop "Lies CLAUDE.md..." \
  --max-iterations 10 \
  --completion-promise "ADR_XXX_COMPLETE"
```

### Final Verify
```bash
./control/verify-with-consultant.sh adr/XXX.md
```

## Python API

```python
from helix.ralph import ConsultantVerifier

verifier = ConsultantVerifier()
result = verifier.verify_adr(Path("adr/040-ralph-automation-pattern.md"))

if result.passed:
    print("PASSED!")
else:
    print(f"FAILED: {result.verdict}")
```

## Best Practices

1. **Kleine Phasen**: Jede Phase sollte in <10min machbar sein
2. **Klare Tests**: Jede Phase hat einen automatischen Test
3. **Consultant am Ende**: Nur 1x Consultant-Call am Ende
4. **Status dokumentieren**: status.md nach jeder Phase updaten
