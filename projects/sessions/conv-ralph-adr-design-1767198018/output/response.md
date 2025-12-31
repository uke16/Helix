# ADR-040: Ralph Automation - Zusammenfassung

## Was wurde erstellt

Das ADR-040 definiert das **Ralph Automation Pattern** - ein standardisiertes System für iterative ADR-Ausführung.

## Kern-Komponenten

### 1. Ralph Section Format für ADRs

Jedes ADR mit `component_type: TOOL|NODE|AGENT|SERVICE|PROCESS` bekommt eine Ralph Section:

```markdown
## Ralph Automation

### Completion Promise
`<promise>ADR_XXX_COMPLETE</promise>`

### Rollen und Kriterien
| Rolle | Promise | Kriterien |
|-------|---------|-----------|
| Developer | `UNIT_TESTS_PASSED` | Tests grün, Syntax OK |
| Integrator | `INTEGRATION_TEST_PASSED` | API + Sub-Agent OK |
| Reviewer | `CODE_REVIEW_PASSED` | ADR Requirements erfüllt |
| Dokumentierer | `DOCS_COMPLETE` | Docs aktualisiert |
```

### 2. Standard Completion Promises

| Rolle | Promise | Wichtigste Kriterien |
|-------|---------|----------------------|
| **Developer** | `UNIT_TESTS_PASSED` | pytest grün, Syntax valid, keine hardcoded Paths |
| **Integrator** | `INTEGRATION_TEST_PASSED` | API startet, Sub-Agent antwortet (>50 Zeichen) |
| **Reviewer** | `CODE_REVIEW_PASSED` | ADR Akzeptanzkriterien erfüllt, Security OK |
| **Dokumentierer** | `DOCS_COMPLETE` | ARCHITECTURE-MODULES.md + Docstrings |

### 3. Sub-Agent Freigabe Pattern

Das kritischste Pattern: Der Integration Test ruft einen anderen Claude auf:

```
Controller (Ralph Loop)
    ↓
Implementiert Code
    ↓
Startet API
    ↓
Ruft Consultant auf (Sub-Agent)
    ↓
Consultant antwortet? → Integration OK
    ↓
<promise>INTEGRATION_TEST_PASSED</promise>
```

## Dateien

**Erstellt:**
- `output/ADR-040-ralph-automation.md` - Das vollständige ADR

**Geplante Implementierung:**
- `src/helix/ralph/controller.py` - Ralph Controller
- `src/helix/ralph/promises.py` - Promise Definitionen
- `docs/RALPH-PATTERN.md` - Dokumentation
- Update `templates/controller/CLAUDE.md.j2`

## Nächste Schritte

1. **Review** - ADR auf Vollständigkeit prüfen
2. **Validieren** - `python -m helix.tools.adr_tool validate output/ADR-040-ralph-automation.md`
3. **Finalisieren** - `python -m helix.tools.adr_tool finalize output/ADR-040-ralph-automation.md`
4. **INDEX.md aktualisieren** - Eintrag hinzufügen

---

*ADR-040 bereit zum Review!*
