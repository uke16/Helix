# Evolution System - Complete Bug Documentation (22.12.2024)

## ✅ FIXED Bugs (1-10)
All template/path issues resolved, /run endpoint implemented.

## 🔴 OPEN CRITICAL BUGS

### Bug 11: /run ignoriert bereits erledigte Phasen
**Location:** `src/helix/api/streaming.py:235`
**Problem:** `run_project_with_streaming(job, project_path, phase_filter=None)` startet ALLE Phasen neu.
**Impact:** Integriertes Projekt wird komplett neu gebaut.
**Fix Required:**
```python
pending = [p.id for p in phases if p.id not in project.phases_completed]
if pending:
    await run_project_with_streaming(job, project_path, phase_filter=pending)
```

### Bug 16: Template/phases.yaml Inkonsistenz 🔴 CRITICAL
**Location:** `templates/developer/_base.md` vs `phases.yaml`
**Problem:**
- Template sagt: "Write all output files to `output/` directory"
- phases.yaml sagt: `new/src/helix/adr/parser.py`

**Evidence:**
```
Phase 2: Claude schrieb → new/     (befolgte phases.yaml)
Phase 3: Claude schrieb → output/  (befolgte Template)
Phase 4: Claude schrieb → output/  (befolgte Template)
Phase 5: Claude schrieb → output/  (befolgte Template)
```

**Workaround:** `consolidate_phase_outputs()` prüft beide Ordner (Bug 7 fix).

**Fix Required:** Template muss phases.yaml output-Pfade verwenden:
```jinja2
## Output Files

Write these files to the following paths:
{% for file in phase.output %}
- {{ file }}
{% endfor %}
```

### Bug 17: Keine Post-Phase Verification 🔴 CRITICAL
**Location:** Missing in `src/helix/api/streaming.py`
**Problem:** Nach Claude Code Run wird NICHT geprüft ob die erwarteten Dateien existieren.

**User Requirement:**
> "hinter jede claude code phase muss noch so ein quality gate... 
> eine python funktion die ihm dann sagt ob alles da ist von meiner seite"

**Current Flow:**
```
1. Claude Code läuft
2. Exit code prüfen
3. → FERTIG (keine File-Verification!)
```

**Required Flow:**
```
1. Claude Code läuft
2. Exit code prüfen
3. Check: Existieren alle files aus phase.output?
4. Check: Sind die Files valide (syntax check)?
5. Wenn nicht: Phase FAILED, detaillierter Error
```

**Implementation Plan:**
```python
async def verify_phase_outputs(phase: Phase, phase_dir: Path) -> VerificationResult:
    """Verify all expected outputs exist after Claude Code run."""
    missing = []
    for expected_file in phase.output:
        # Check both output/ and phases.yaml path
        paths_to_check = [
            phase_dir / "output" / expected_file.lstrip("new/").lstrip("modified/"),
            phase_dir / expected_file,
        ]
        if not any(p.exists() for p in paths_to_check):
            missing.append(expected_file)
    
    return VerificationResult(
        success=len(missing) == 0,
        missing_files=missing
    )
```

## 🟡 MEDIUM BUGS

### Bug 12: Kein Guard für integrierte Projekte
**Location:** `src/helix/api/routes/evolution.py`
**Problem:** `/run` auf "integrated" Projekt startet alles neu.
**Fix:** Status-Check mit `force` parameter (teilweise implementiert).

### Bug 18: Template erhält nicht alle Phase-Infos
**Location:** `src/helix/api/streaming.py:75-90`
**Problem:** Template-Context hat nicht die output-Pfade aus phases.yaml.

**Current:**
```python
context = {
    "phase_id": phase.id,
    "phase_name": phase.name,
    "phase_type": phase.type,
    "phase_description": getattr(phase, 'description', '') or "",
    "project_path": str(project_path),
}
```

**Required:**
```python
context = {
    ...
    "phase_output": phase.output,  # ["new/src/helix/adr/parser.py", ...]
    "phase_input": phase.input,    # ["CONCEPT.md", ...]
    "quality_gate": phase.quality_gate,
}
```

## ⚠️ KNOWN ISSUES (Non-blocking)

### Bug 9: Pre-existing Test Failures
44 fixture errors, 9 API mismatches - unrelated to Evolution system.

## Summary Table

| Bug | Severity | Status | Blocking |
|-----|----------|--------|----------|
| 11 | Critical | Open | YES |
| 16 | Critical | Open | YES |
| 17 | Critical | Open | YES |
| 12 | Medium | Partial | NO |
| 18 | Medium | Open | NO |
| 9 | Low | Known | NO |

## Recommended Fix Order

1. **Bug 17** - Post-phase verification (most impactful)
2. **Bug 16** - Template/phases.yaml consistency
3. **Bug 18** - Pass phase info to template
4. **Bug 11** - Skip completed phases
5. **Bug 12** - Guard integrated projects
