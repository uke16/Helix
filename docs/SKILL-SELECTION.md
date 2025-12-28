# Intelligent Skill Selection

> ADR-020: Automatic skill recommendation based on request analysis.

This module provides intelligent discovery and selection of HELIX skills based on user requests.
It enables the Consultant agent to efficiently find relevant documentation without reading all available skills.

## Overview

The Skill Selection system consists of three components:

| Component | Purpose |
|-----------|---------|
| **Skill Index** | Auto-generated `INDEX.yaml` with extracted keywords |
| **Skill Selector** | Matches requests against skills using scoring |
| **Reverse Index** | Maps source files to their originating ADRs |

## Quick Start

### Select Skills for a Request

```python
from helix.docs.skill_selector import SkillSelector

selector = SkillSelector()
matches = selector.select("BOM Export für SAP", top_n=3)

for match in matches:
    print(f"{match.path}: {match.score} ({match.matched_keywords})")
```

### Generate Skill Index

```bash
python -m helix.docs.skill_index
# Output: skills/INDEX.yaml
```

### Lookup File Origin

```python
from helix.docs.reverse_index import ReverseIndex

index = ReverseIndex()
info = index.lookup("src/helix/debug/stream_parser.py")

if info:
    print(f"Created by: {info.created_by}")
    print(f"ADR file: {info.adr_file}")
```

---

## Skill Index (`skills/INDEX.yaml`)

The skill index is an auto-generated YAML file containing metadata for all SKILL.md files.

### Structure

```yaml
_meta:
  generated_at: "2024-12-28T10:00:00Z"
  generator: "helix.docs.skill_index"

skills:
  - path: skills/pdm/SKILL.md
    name: "PDM - Product Data Management"
    description: "BOM, Artikel, Stücklisten, SAP-Integration"

    # AUTO-EXTRACTED from SKILL.md content
    auto_keywords:
      - BOM
      - Artikel
      - Stückliste
      - SAP

    # MANUAL - for synonyms (preserved on regeneration)
    aliases:
      - Bill of Materials
      - Produktdaten

    # MANUAL - phrase triggers (preserved on regeneration)
    triggers:
      - "wenn BOM oder Stückliste erwähnt"
      - "wenn SAP-Integration benötigt"
```

### Keyword Extraction

Keywords are automatically extracted from SKILL.md files:

| Source | Example |
|--------|---------|
| Headers (`##`, `###`) | `## BOM Management` → `BOM`, `Management` |
| Code terms (backticks) | `` `get_article` `` → `get_article` |
| Bold terms | `**Stückliste**` → `Stückliste` |
| Method names | `create_bom()` → `create_bom` |

Noise words (articles, prepositions, common terms) are filtered out.

### Regeneration

```bash
# Regenerate from all SKILL.md files
python -m helix.docs.skill_index

# Custom paths
python -m helix.docs.skill_index --skills-dir skills/ --output skills/INDEX.yaml
```

Manual fields (`aliases`, `triggers`) are preserved during regeneration.

---

## Skill Selector

The selector matches user requests against the skill index using a scoring algorithm.

### Scoring Algorithm

| Match Type | Points | Description |
|------------|--------|-------------|
| Exact keyword | 10 | Request word matches keyword exactly |
| Substring | 3 | Partial match between request and keyword |
| Alias | 10 | Request matches a skill alias |
| Trigger | 15 | Request matches a trigger phrase |

### Usage

```python
from helix.docs.skill_selector import SkillSelector, SkillMatch

selector = SkillSelector()

# Select top 3 skills for a request
matches: list[SkillMatch] = selector.select(
    request="BOM Export für SAP",
    top_n=3
)

# Each match contains:
# - path: str          (e.g., "skills/pdm/SKILL.md")
# - score: int         (e.g., 25)
# - matched_keywords: list[str]  (e.g., ["BOM", "SAP"])
# - name: str          (skill name)
# - description: str   (skill description)
```

### Fallback Behavior

- **No matches**: Returns all skills (score=0)
- **Low scores**: Skills with score < 5 are not recommended
- **Always include**: `skills/helix/SKILL.md` for HELIX-related tasks

### CLI

```bash
# Select skills for a request
python -m helix.docs.skill_selector "BOM Export für SAP"

# List all skills
python -m helix.docs.skill_selector --all

# Custom top N
python -m helix.docs.skill_selector "database query" --top-n 5
```

### Markdown Output

```python
# Format for CLAUDE.md template injection
table = selector.format_recommendations(matches)
print(table)
```

Output:
```
| Skill | Score | Matched Keywords |
|-------|-------|------------------|
| skills/pdm/SKILL.md | 25 | BOM, SAP, Export |
| skills/infrastructure/SKILL.md | 10 | SAP |
```

---

## Reverse Index (CODE → ADR)

The reverse index maps source files back to their originating ADRs for traceability.

### File Categories

| Status | Description |
|--------|-------------|
| `tracked` | File has ADR reference and exists |
| `untracked` | File exists but no ADR (legacy, tests) |
| `orphaned` | ADR says "create" but file is missing |

### Usage

```python
from helix.docs.reverse_index import ReverseIndex, FileInfo

index = ReverseIndex()

# Lookup a single file
info: FileInfo | None = index.lookup("src/helix/debug/stream_parser.py")

if info:
    print(f"Status: {info.status}")
    print(f"Created by: {info.created_by}")
    print(f"ADR file: {info.adr_file}")
    print(f"Modified by: {info.modified_by}")

# Get all orphaned files
orphaned = index.get_orphaned()

# Get all files for an ADR
files = index.get_by_adr("013")

# Get statistics
stats = index.get_statistics()
print(f"Coverage: {stats['coverage_percent']}%")
```

### CLI

```bash
# Lookup a file
python -m helix.docs.reverse_index lookup src/helix/debug/stream_parser.py

# Show statistics
python -m helix.docs.reverse_index stats

# List orphaned files
python -m helix.docs.reverse_index orphaned

# Files by ADR
python -m helix.docs.reverse_index by-adr 013
```

---

## ADR Files Validation

Quality gate that validates ADR file declarations exist.

### Purpose

Detects issues with ADR data quality:
- ADRs marked "Implemented" with missing files
- Stale ADR references after file removals
- Incorrect file paths in ADR declarations

### Usage

```python
from helix.quality_gates.adr_files_exist import ADRFilesExistGate

gate = ADRFilesExistGate(project_root=Path("."))
result = await gate.check()

if not result.passed:
    print(f"Found {len(result.details['missing'])} missing files")
    print(gate.format_report(result))
```

### CLI

```bash
# Validate ADR files
python -m helix.quality_gates.adr_files_exist

# JSON output
python -m helix.quality_gates.adr_files_exist --json

# Strict mode (also check files.modify)
python -m helix.quality_gates.adr_files_exist --strict
```

### Example Output

```
ADR Files Validation
========================================

FAILED: 3 missing files in 1 Implemented ADR(s)

ADRs checked: 5
  Valid: 4
  Invalid: 1

Invalid ADRs:
  ADR-009: 0/3 files exist
    Title: Bootstrap Project
    Suggestion: status should be 'Proposed'
    Missing: src/helix/bootstrap/runner.py
    Missing: src/helix/bootstrap/config.py
    Missing: src/helix/bootstrap/templates/
```

---

## Integration with Phase Executor

The skill selector integrates with the HELIX phase executor for consultant phases.

### In `phase_executor.py`

```python
async def _prepare_consultant_phase(self, phase_dir: Path, request: str):
    """Prepare consultant phase with skill recommendations."""
    selector = SkillSelector()
    recommended = selector.select(request)

    # Inject into CLAUDE.md template context
    context["recommended_skills"] = recommended
    context["all_skills"] = selector.all_skills()
```

### In `phase-claude.md.j2`

```jinja2
{% if phase.type == "consultant" and recommended_skills %}
## Empfohlene Skills (AUTO-SELECTED)

Basierend auf dem Request wurden diese Skills ausgewählt:

| Skill | Score | Matched Keywords |
|-------|-------|------------------|
{% for skill in recommended_skills %}
| {{ skill.path }} | {{ skill.score }} | {{ skill.matched_keywords | join(", ") }} |
{% endfor %}

→ **Lies diese Skills zuerst!**

## Andere verfügbare Skills
{% for skill in all_skills if skill not in recommended_skills %}
- {{ skill.path }}
{% endfor %}
{% endif %}
```

---

## Configuration

### Scoring Weights

The selector uses configurable scoring weights:

```python
class SkillSelector:
    EXACT_MATCH_SCORE = 10    # Exact keyword match
    SUBSTRING_MATCH_SCORE = 3  # Partial match
    TRIGGER_MATCH_SCORE = 15   # Trigger phrase match
    ALIAS_MATCH_SCORE = 10     # Alias match
    MIN_RECOMMEND_SCORE = 5    # Minimum score to recommend
    DEFAULT_TOP_N = 3          # Default number of results
```

### Noise Words

Common words are filtered during keyword extraction:
- English: `the`, `a`, `and`, `or`, `with`, `for`, etc.
- German: `der`, `die`, `das`, `und`, `oder`, `mit`, `für`, etc.
- Technical: `example`, `note`, `see`, `usage`, etc.

---

## Related Documentation

- [ADR-020: Intelligent Documentation Discovery](../ADR-020.md)
- [ADR-014: Documentation Architecture](../../adr/014-documentation-architecture.md)
- [ADR-019: Documentation as Code](../../adr/019-docs-as-code.md)
