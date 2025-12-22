# Evolution System - Bug Tracker

**Last Updated:** 2024-12-22

## Summary

| Category | Count |
|----------|-------|
| Fixed | 10 |
| Open Critical | 3 |
| Open Medium | 2 |
| Known/Won't Fix | 1 |

## ✅ Fixed Bugs (1-10)

- **Bug 1-5:** Template path issues
- **Bug 6-8:** Template system integration
- **Bug 10:** `/run` endpoint implemented

## 🔴 Open Critical Bugs

### Bug 11: /run ignores completed phases

**Location:** `src/helix/api/streaming.py:235`

**Problem:** `run_evolution_pipeline` calls `run_project_with_streaming(phase_filter=None)`,
which runs ALL phases regardless of `status.json.phases_completed`.

**Impact:** Re-running on integrated project rebuilds everything.

**Fix:**
```python
pending = [p.id for p in phases if p.id not in project.phases_completed]
await run_project_with_streaming(job, project_path, phase_filter=pending)
```

### Bug 16: Template/phases.yaml output path inconsistency

**Location:** `templates/developer/_base.md` vs `phases.yaml`

**Problem:**
- Template says: "Write to `output/` directory"
- phases.yaml says: `new/src/helix/adr/parser.py`

**Evidence:**
```
Phase 2: wrote to new/     (followed phases.yaml)
Phase 3: wrote to output/  (followed template)
Phase 4: wrote to output/  (followed template)
```

**Workaround:** `consolidate_phase_outputs()` checks both directories.

**Fix:** Template should show files from phases.yaml:
```jinja2
## Expected Output Files
{% for file in phase.output %}
- {{ file }}
{% endfor %}
```

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
4. Verify syntax
5. If missing: FAILED with detailed error
```

**Fix:** See ADR-001 for ADR-based verification approach.

## 🟡 Open Medium Bugs

### Bug 12: No guard for integrated projects

**Location:** `src/helix/api/routes/evolution.py`

**Status:** Partially fixed (force parameter added, but not fully tested)

### Bug 18: Template missing phase info

**Location:** `src/helix/api/streaming.py:75-90`

**Problem:** Template context doesn't include `phase.output` paths.

**Fix:** Add to context:
```python
context = {
    ...
    "phase_output": phase.output,
    "phase_input": phase.input,
}
```

## ⚠️ Known Issues

### Bug 9: Pre-existing test failures

44 fixture errors, 9 API mismatches - unrelated to Evolution system.
These are in other modules and don't block Evolution functionality.

## Architecture Improvements

See [ADR-001: ADR as Single Source of Truth](../adr/001-adr-as-single-source-of-truth.md)
for the planned architectural changes that will address bugs 16, 17, and 18.

**Key Changes:**
1. ADR replaces spec.yaml as Single Source of Truth
2. Post-phase verification uses ADR.files
3. Templates show expected files from ADR
4. Acceptance criteria tracked through workflow
