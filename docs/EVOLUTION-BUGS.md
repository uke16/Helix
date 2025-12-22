# Evolution System - Bug Status

## Fixed Bugs ✅

### Bug 1: Phase Output vs new/modified Struktur ✅
- **Fix:** `consolidate_phase_outputs()` in project.py + deployer.py integration
- **Commit:** Already in main

### Bug 2: status.json Status "planning" nicht erkannt ✅
- **Fix:** Added `PLANNING = "planning"` to EvolutionStatus enum
- **Commit:** Already in main

### Bug 4: Validate Message doesn't show errors ✅
- **Fix:** Added error count to validation message
- **Commit:** Already in main

### Bug 6: streaming.py generiert keine CLAUDE.md ✅
- **Fix:** Added TemplateEngine integration in streaming.py
- **Commit:** Already in main

### Bug 7: Template expects 'project' but context has flat structure ✅
- **Fix:** Updated _base.md to use available context variables
- **Commit:** This commit

### Bug 8: Template extends path incorrect ✅
- **Fix:** Changed `{% extends "_base.md" %}` to `{% extends "developer/_base.md" %}`
- **Commit:** This commit

## Open Issues 🔴

### Bug 3: Circular Import in quality_gates Package
- **Status:** ADR-System issue, not workflow
- **Fix:** Phase 4 needs to put adr_gate in helix.adr.gate instead of quality_gates/

### Bug 5: Evolution Project shows 0 files after deploy
- **Status:** Cosmetic - deploy works, just count display wrong
- **TODO:** Check list_new_files() after consolidation
