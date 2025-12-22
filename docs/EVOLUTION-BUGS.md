# Evolution System - Bug Tracker

**Last Updated:** 2024-12-22

## Summary

| Category | Count |
|----------|-------|
| Fixed | 12 |
| Open Critical | 1 |
| Open Medium | 1 |
| Known/Won't Fix | 1 |

## ✅ Fixed Bugs (1-12)

### Bug 1-10: Template/Path/API issues
All resolved in previous sessions.

### Bug 11: /run ignores completed phases ✅ FIXED
**Fix:** `run_evolution_pipeline` now reads `phases_completed` from status.json
and only executes pending phases.

```python
# Calculate pending phases
pending_phases = [pid for pid in all_phase_ids if pid not in phases_completed]
if not pending_phases:
    # Skip to deploy
else:
    await run_project_with_streaming(job, project_path, phase_filter=pending_phases)
```

### Bug 12: No guard for integrated projects ✅ FIXED
**Fix:** `/run` endpoint returns error if project is already integrated:
```json
{"detail": "Project already integrated. Use force=true to re-run all phases."}
```

## 🔴 Open Critical Bugs

### Bug 17: No post-phase file verification

**Location:** Missing in `src/helix/api/streaming.py`

**Problem:** After Claude Code run, no check if expected files exist.

**Current Flow:**
```
1. Claude Code runs
2. Check exit code
3. → DONE (no file verification!)
```

**Required Flow:**
```
1. Claude Code runs
2. Check exit code
3. Verify files from phases.yaml output exist
4. Verify syntax (for code files)
5. If missing: FAILED with detailed error
```

## 🟡 Open Medium Bugs

### Bug 16: Template/phases.yaml output path inconsistency

**Problem:**
- Template says: "Write to `output/` directory"
- phases.yaml defines: `new/src/helix/module.py`

**Workaround:** `consolidate_phase_outputs()` checks both directories.

**Proper Fix:** Template should show expected files from phases.yaml or ADR.

## ⚠️ Known Issues

### Bug 9: Pre-existing test failures
44 fixture errors, 9 API mismatches - unrelated to Evolution system.

## Verification

```bash
# Test Bug 11 fix (partial completion)
# Project with phases 1,2,3 and phase 1 completed:
# → Only runs phases 2 and 3

# Test Bug 12 fix (integrated guard)
curl -X POST http://localhost:8001/helix/evolution/projects/adr-system/run
# → Returns: "Project already integrated. Use force=true to re-run all phases."
```
