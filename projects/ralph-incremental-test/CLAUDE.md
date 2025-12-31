# Incremental Goals Test

## WICHTIG: Inkrementelles Arbeiten

Arbeite Phase für Phase:

### Phase 1: Basic Calculator
```bash
# Erstelle calculator.py mit add(), subtract()
# Erstelle test_calculator.py mit test_add, test_subtract
# TEST: python3 -m pytest test_calculator.py -v
# Wenn GRÜN → weiter zu Phase 2
```

### Phase 2: Advanced Operations
```bash
# Erweitere calculator.py mit multiply(), divide()
# Erweitere test_calculator.py mit test_multiply, test_divide
# TEST: python3 -m pytest test_calculator.py -v
# Wenn GRÜN → weiter zu Phase 3
```

### Phase 3: History Feature
```bash
# Füge history hinzu
# TEST: python3 -m pytest test_calculator.py -v
# Wenn GRÜN → FINAL CHECK
```

### FINAL: Consultant Freigabe
```bash
# Rufe Consultant auf für finale Freigabe:
/home/aiuser01/helix-v4/control/spawn-consultant.sh "
Prüfe ob Test-ADR komplett ist:
- calculator.py mit add, subtract, multiply, divide, get_history
- test_calculator.py mit 5 Tests
- pytest GRÜN
Antworte: PASSED oder FAILED
"
```

Wenn Consultant PASSED sagt:
<promise>CALCULATOR_COMPLETE</promise>
