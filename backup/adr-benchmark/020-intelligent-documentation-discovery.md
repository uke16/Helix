---
adr_id: "020"
title: "Intelligent Documentation Discovery"
status: Proposed
date: 2024-12-24

project_type: helix_internal
component_type: TOOL
classification: NEW
change_scope: major

domain: helix
language: python
skills:
  - helix

files:
  create:
    - src/helix/docs/skill_index.py
    - src/helix/docs/skill_selector.py
    - src/helix/docs/reverse_index.py
    - src/helix/quality_gates/adr_files_exist.py
    - skills/INDEX.yaml
    - tests/docs/test_skill_selector.py
    - tests/docs/test_reverse_index.py
  modify:
    - src/helix/tools/adr_tool.py
    - src/helix/orchestrator/phase_executor.py
    - docs/templates/phase-claude.md.j2
    - adr/INDEX.md
  docs:
    - skills/helix/SKILL.md
    - docs/SKILL-SELECTION.md

depends_on:
  - "014"  # Documentation Architecture
  - "019"  # Documentation as Code

related_to:
  - "005"  # Consultant Topology
  - "017"  # Phase Orchestrator
---

# ADR-020: Intelligent Documentation Discovery

## Status

Proposed

---

## Kontext

HELIX v4 hat ein wachsendes Dokumentationssystem mit mehreren Skills und ADRs. Aktuell gibt es vier Probleme:

### Problem 1: Consultant liest alle Skills

Der Consultant Agent hat keine Möglichkeit zu wissen, welche Skills relevant sind. Er muss entweder alle lesen (teuer, ~5000 Zeilen) oder raten.

```
Aktuell:
  Request: "BOM Export für SAP"
  Consultant: *liest alle 7 Skills*
  → 5000+ Zeilen Context, davon 80% irrelevant
```

### Problem 2: Kein Skill-Überblick

Es gibt keinen Index der verfügbaren Skills. `skills/INDEX.md` existiert nicht.

```
skills/
├── encoder/SKILL.md     # Was steht hier?
├── helix/SKILL.md       # Keine Übersicht
├── infrastructure/      # verfügbar
├── lsp/SKILL.md
└── pdm/SKILL.md
```

### Problem 3: Keine Traceability CODE → ADR

Wenn man eine Datei sieht, weiß man nicht welches ADR sie erstellt hat.

```
src/helix/debug/stream_parser.py
  → Warum existiert diese Datei?
  → Welches ADR hat sie spezifiziert?
  → Welche anderen ADRs haben sie modifiziert?
```

### Problem 4: ADR Status kann falsch sein

Ein ADR kann "Implemented" sagen, aber die spezifizierten Dateien existieren nicht.

```yaml
# adr/009-bootstrap-project.md
status: Implemented  # ← FALSCH!
files:
  create:
    - src/helix/bootstrap/runner.py  # ← Existiert nicht!
```

---

## Entscheidung

Wir implementieren vier Features für intelligente Dokumentations-Discovery:

### Feature 1: Skill Index (skills/INDEX.yaml)

Automatisch generierter Index aller Skills mit Keywords für Matching.

```yaml
# skills/INDEX.yaml
_meta:
  generated_at: "2024-12-24T10:00:00Z"
  generator: "helix.docs.skill_index"

skills:
  - path: skills/pdm/SKILL.md
    name: "PDM - Product Data Management"
    description: "BOM, Artikel, Stücklisten, SAP-Integration"
    
    # AUTO-EXTRACTED (aus SKILL.md)
    auto_keywords:
      - BOM
      - Artikel
      - get_article
      - create_bom
      - Stückliste
    
    # MANUELL (für Synonyme)
    aliases:
      - Bill of Materials
      - Produktdaten
      - SAP
    
    # SCOPE TRIGGERS
    triggers:
      - "wenn BOM oder Stückliste erwähnt"
      - "wenn SAP-Integration benötigt"
```

### Feature 2: Smart Skill Selection

Automatische Empfehlung relevanter Skills basierend auf Request.

```python
# Consultant Phase erhält:
## Empfohlene Skills (AUTO-SELECTED)

| Skill | Score | Matched |
|-------|-------|---------|
| skills/pdm/SKILL.md | 25 | BOM, SAP, Export |
| skills/infrastructure/SKILL.md | 10 | SAP |

→ Lies diese Skills zuerst!
```

**Algorithmus:**
1. Keywords aus Request extrahieren
2. Gegen auto_keywords + aliases matchen
3. Score berechnen (exact match: 10, substring: 3, trigger: 15)
4. Top 3 empfehlen, Rest auflisten

**Fallback-Garantien:**
- Kein Match → Alle Skills anzeigen
- Score < 5 → Nicht empfehlen
- Always include: skills/helix/SKILL.md

### Feature 3: Reverse Index (CODE → ADR)

On-Demand generierter Index: Welche Datei wurde von welchem ADR erstellt?

```bash
$ python -m helix.tools.adr_tool code-to-adr src/helix/debug/stream_parser.py

src/helix/debug/stream_parser.py:
  created_by: ADR-013
  adr_file: adr/013-debug-observability-engine.md
  history:
    - ADR-013: create (2024-12-23)
```

**Drei Kategorien:**
- `tracked`: Datei hat ADR-Referenz
- `untracked`: Datei existiert, kein ADR (Legacy, Tests)
- `orphaned`: ADR sagt "create", aber Datei fehlt

### Feature 4: ADR Files Validation

Quality Gate das prüft ob ADR files.create wirklich existieren.

```bash
$ python -m helix.tools.adr_tool validate-files

ADR Files Validation:
━━━━━━━━━━━━━━━━━━━━
✅ ADR-013: 5/5 files exist
✅ ADR-017: 4/4 files exist
⚠️ ADR-009: 0/3 files exist (status should be "Proposed")
   Missing:
   - src/helix/bootstrap/runner.py
   - src/helix/bootstrap/config.py
   - src/helix/bootstrap/templates/

Total: 2 valid, 1 warning
```

---

## Implementation

### Phase 1: Skill Index Generator (Tag 1)

```
files.create:
  - src/helix/docs/skill_index.py
  - skills/INDEX.yaml
```

**skill_index.py:**
```python
class SkillIndexGenerator:
    def extract_keywords(self, skill_path: Path) -> set[str]:
        """Extract keywords from SKILL.md."""
        content = skill_path.read_text()
        
        # Headers, code terms, bold terms
        headers = re.findall(r'^#+\s+(.+)$', content, re.M)
        code_terms = re.findall(r'`([^`]+)`', content)
        bold_terms = re.findall(r'\*\*([^*]+)\*\*', content)
        
        return self._filter_noise(headers + code_terms + bold_terms)
    
    def generate_index(self) -> dict:
        """Generate skills/INDEX.yaml."""
        skills = []
        for skill_file in self.skills_dir.rglob("SKILL.md"):
            skills.append({
                "path": str(skill_file),
                "auto_keywords": list(self.extract_keywords(skill_file)),
                "aliases": [],  # Manually maintained
                "triggers": []  # Manually maintained
            })
        return {"skills": skills}
```

### Phase 2: Skill Selector (Tag 2)

```
files.create:
  - src/helix/docs/skill_selector.py
  - tests/docs/test_skill_selector.py
```

**skill_selector.py:**
```python
class SkillSelector:
    def __init__(self, index_path: Path = Path("skills/INDEX.yaml")):
        self.index = yaml.safe_load(index_path.read_text())
    
    def select(self, request: str, top_n: int = 3) -> list[SkillMatch]:
        """Select relevant skills for a request."""
        request_words = set(tokenize(request.lower()))
        
        scored = []
        for skill in self.index["skills"]:
            all_keywords = set(skill["auto_keywords"]) | set(skill.get("aliases", []))
            
            # Exact matches (high weight)
            exact = request_words & {k.lower() for k in all_keywords}
            score = len(exact) * 10
            
            # Substring matches (medium weight)
            for kw in all_keywords:
                if any(kw.lower() in w or w in kw.lower() for w in request_words):
                    score += 3
            
            # Trigger matches (high weight)
            for trigger in skill.get("triggers", []):
                if self._matches_trigger(request, trigger):
                    score += 15
            
            if score > 0:
                scored.append(SkillMatch(skill["path"], score, exact))
        
        # Sort by score, return top N
        scored.sort(key=lambda x: -x.score)
        return scored[:top_n] if scored else self._fallback_all()
```

### Phase 3: Reverse Index (Tag 3)

```
files.create:
  - src/helix/docs/reverse_index.py
  - tests/docs/test_reverse_index.py
files.modify:
  - src/helix/tools/adr_tool.py
```

**reverse_index.py:**
```python
class ReverseIndex:
    def __init__(self, adr_dir: Path = Path("adr")):
        self.adr_dir = adr_dir
    
    def build(self) -> dict[str, FileInfo]:
        """Build reverse index from all ADRs."""
        index = {}
        
        for adr_file in self.adr_dir.glob("*.md"):
            header = self._parse_header(adr_file)
            adr_id = header.get("adr_id")
            
            for f in header.get("files", {}).get("create", []):
                index[f] = FileInfo(
                    created_by=f"ADR-{adr_id}",
                    adr_file=str(adr_file),
                    exists=Path(f).exists()
                )
            
            for f in header.get("files", {}).get("modify", []):
                if f in index:
                    index[f].modified_by.append(f"ADR-{adr_id}")
                else:
                    index[f] = FileInfo(modified_by=[f"ADR-{adr_id}"])
        
        return index
    
    def lookup(self, file_path: str) -> FileInfo | None:
        """Lookup ADR info for a specific file."""
        index = self.build()
        return index.get(file_path)
```

### Phase 4: ADR Files Gate (Tag 4)

```
files.create:
  - src/helix/quality_gates/adr_files_exist.py
files.modify:
  - adr/INDEX.md
```

**adr_files_exist.py:**
```python
class ADRFilesExistGate:
    name = "adr_files_exist"
    description = "Validates that files declared in ADR headers exist"
    
    async def check(self) -> GateResult:
        issues = []
        
        for adr_file in self.adr_dir.glob("*.md"):
            header = parse_adr_header(adr_file)
            if header.get("status") != "Implemented":
                continue  # Only check implemented ADRs
            
            for f in header.get("files", {}).get("create", []):
                if not Path(f).exists():
                    issues.append(f"ADR-{header['adr_id']}: {f} not found")
        
        if issues:
            return GateResult(
                passed=False,
                message=f"{len(issues)} missing files in Implemented ADRs",
                details={"missing": issues}
            )
        
        return GateResult(passed=True, message="All ADR files exist")
```

### Phase 5: Integration (Tag 5)

```
files.modify:
  - src/helix/orchestrator/phase_executor.py
  - docs/templates/phase-claude.md.j2
```

**In phase_executor.py:**
```python
async def _prepare_consultant_phase(self, phase_dir: Path, request: str):
    """Prepare consultant phase with skill recommendations."""
    selector = SkillSelector()
    recommended = selector.select(request)
    
    # Inject into CLAUDE.md template context
    context["recommended_skills"] = recommended
    context["all_skills"] = selector.all_skills()
```

**In phase-claude.md.j2:**
```jinja2
{% if phase.type == "consultant" and recommended_skills %}
## Empfohlene Skills (AUTO-SELECTED)

Basierend auf dem Request wurden diese Skills ausgewählt:

| Skill | Score | Matched Keywords |
|-------|-------|------------------|
{% for skill in recommended_skills %}
| {{ skill.path }} | {{ skill.score }} | {{ skill.matches | join(", ") }} |
{% endfor %}

→ **Lies diese Skills zuerst!**

## Andere verfügbare Skills
{% for skill in all_skills if skill not in recommended_skills %}
- {{ skill.path }}
{% endfor %}
{% endif %}
```

---

## Dokumentation

### Zu aktualisierende Dokumentation

| Datei | Änderung |
|-------|----------|
| `skills/helix/SKILL.md` | Neue Section "Skill Selection" |
| `adr/INDEX.md` | File validation warnings |
| `docs/sources/consultant-workflow.yaml` | Smart Selection Workflow |

### Neue Dokumentation

| Datei | Inhalt |
|-------|--------|
| `docs/SKILL-SELECTION.md` | Übersicht Smart Selection |
| `skills/INDEX.yaml` | Auto-generated Skill Index |

---

## Akzeptanzkriterien

### Must Have

- [ ] `skills/INDEX.yaml` wird automatisch generiert
- [ ] Keywords werden aus SKILL.md extrahiert (headers, code, bold)
- [ ] `SkillSelector.select(request)` gibt Top-3 Skills zurück
- [ ] Fallback: Wenn kein Match → alle Skills
- [ ] `adr_tool code-to-adr <file>` zeigt ADR-Herkunft
- [ ] `adr_tool validate-files` prüft ADR files.create
- [ ] Consultant Phase zeigt empfohlene Skills

### Should Have

- [ ] Manuelle `aliases` in INDEX.yaml für Synonyme
- [ ] `triggers` für Phrasen-Matching
- [ ] Warnings in adr/INDEX.md bei fehlenden Dateien
- [ ] Coverage Report: "X% of files tracked by ADR"

### Nice to Have

- [ ] VS Code Extension für "Go to ADR"
- [ ] Pre-commit Hook warnt bei untracked files
- [ ] Automatische INDEX.yaml Regenerierung bei SKILL.md Änderung

---

## Konsequenzen

### Vorteile

1. **Effizienter Consultant**: Liest nur relevante Skills
2. **Übersicht**: skills/INDEX.yaml zeigt alle verfügbaren Skills
3. **Traceability**: Jede Datei kann zu ihrem ADR zurückverfolgt werden
4. **Datenqualität**: Falsche ADR-Status werden erkannt

### Nachteile

1. **Zusätzliche Komplexität**: Neues Subsystem zu maintainen
2. **Manuelle Pflege**: aliases und triggers müssen gepflegt werden
3. **False Positives**: Keyword-Matching kann falsch liegen

### Risiken

| Risiko | Wahrscheinlichkeit | Mitigation |
|--------|-------------------|------------|
| Skill Selection empfiehlt falsche Skills | Mittel | Fallback + Override |
| INDEX.yaml wird nicht aktualisiert | Niedrig | Pre-commit Hook |
| Reverse Index zu langsam | Sehr niedrig | ~20 ADRs, <1 Sekunde |

---

## Referenzen

- ADR-005: Consultant Topology
- ADR-014: Documentation Architecture
- ADR-019: Documentation as Code
- Consultant Meeting Notes: projects/adr-020-discovery/consultant-notes.md

---

## Changelog

- 2024-12-24: Initial specification (Consultant Meeting)
