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
    - src/helix/discovery/__init__.py
    - src/helix/discovery/skill_registry.py
    - src/helix/discovery/keyword_matcher.py
    - src/helix/discovery/adr_tracer.py
    - skills/manifest.yaml
  modify:
    - src/helix/tools/docs_compiler.py
    - skills/helix/SKILL.md
  docs:
    - skills/helix/SKILL.md
    - CLAUDE.md
depends_on:
  - "014"
---

# ADR-020: Intelligent Documentation Discovery

## Kontext

### Problem: Consultant liest zu viel

Der Consultant Agent muss aktuell ALLE Skills lesen (~5000 Zeilen) obwohl meist nur 1-2 relevant sind.

**Beispiel:**
```
User fragt nach "BOM Export für SAP"
→ Consultant liest: helix/, encoder/, infrastructure/, pdm/, lsp/
→ Aber nur pdm/ und infrastructure/ wären relevant gewesen
```

Das führt zu:
- **Hohen Token-Kosten** (~5000 Zeilen × jede Consultant-Session)
- **Langsameren Responses** (mehr zu verarbeiten)
- **Noise** (irrelevante Informationen im Kontext)

### Problem: Fehlende Übersicht

Es gibt keinen zentralen Index welche Skills existieren und wofür sie sind:
- Skills sind in verschiedenen Verzeichnissen verstreut (`skills/pdm/`, `skills/encoder/`, etc.)
- Keine maschinenlesbaren Keywords
- Consultant muss raten welche Skills relevant sein könnten

### Problem: ADR-Traceability

Wenn eine Datei existiert, weiß man nicht:
- Welches ADR hat sie erstellt?
- Ist das ADR implementiert oder nur proposed?
- Welche anderen Dateien gehören zum selben Feature?

**Risiko:** ADR sagt "Implemented" aber Dateien fehlen oder sind veraltet.

## Entscheidung

Wir implementieren ein **Intelligent Documentation Discovery System** mit drei Komponenten:

### 1. Skill Registry (Manifest)

Eine zentrale `skills/manifest.yaml` die alle Skills indiziert:

```yaml
# skills/manifest.yaml
_meta:
  version: "1.0"
  description: "Central registry of all HELIX skills"

skills:
  pdm:
    path: skills/pdm/SKILL.md
    description: "Product Data Management - Artikel, BOMs, Katalog"
    keywords:
      - article
      - artikel
      - bom
      - stückliste
      - catalog
      - katalog
      - sap
      - erp
      - product
      - revision
    domains:
      - pdm
      - data
    priority: 1  # 1=core, 2=domain, 3=tools

  encoder:
    path: skills/encoder/SKILL.md
    description: "POSITAL Encoder Produkte und Konfiguration"
    keywords:
      - encoder
      - posital
      - sensor
      - drehgeber
      - inkremental
      - absolut
      - ssi
      - biss
    domains:
      - encoder
      - product
    priority: 2

  infrastructure:
    path: skills/infrastructure/SKILL.md
    description: "Docker, PostgreSQL, Deployment"
    keywords:
      - docker
      - postgres
      - database
      - deployment
      - server
      - container
      - migration
      - sql
    domains:
      - infrastructure
      - devops
    priority: 2

  helix:
    path: skills/helix/SKILL.md
    description: "HELIX Orchestration System"
    keywords:
      - helix
      - orchestrat
      - phase
      - quality gate
      - consultant
      - claude
      - adr
    domains:
      - helix
    priority: 1
    sub_skills:
      - path: skills/helix/adr/SKILL.md
        keywords: [adr, architecture decision]
      - path: skills/helix/evolution/SKILL.md
        keywords: [evolution, self-modification]

  lsp:
    path: skills/lsp/SKILL.md
    description: "Language Server Protocol für Code-Intelligence"
    keywords:
      - lsp
      - definition
      - reference
      - hover
      - symbol
      - refactor
      - navigation
    domains:
      - development-tools
    priority: 3
```

### 2. Keyword Matcher

Ein leichtgewichtiger Matcher der User-Requests analysiert:

```python
# src/helix/discovery/keyword_matcher.py

class KeywordMatcher:
    """Matches user requests to relevant skills without embeddings."""

    def __init__(self, manifest_path: Path):
        self.manifest = self._load_manifest(manifest_path)
        self._build_index()

    def match(self, query: str, max_skills: int = 3) -> list[SkillMatch]:
        """
        Find skills matching a user query.

        Uses:
        1. Exact keyword matches (highest score)
        2. Partial/fuzzy matches (lower score)
        3. Domain matches (fallback)

        Returns skills sorted by relevance score.
        """
        query_lower = query.lower()
        query_words = set(query_lower.split())

        scores: dict[str, float] = {}

        for skill_id, skill_info in self.manifest["skills"].items():
            score = 0.0

            # Exact keyword match: +10 points per match
            for keyword in skill_info.get("keywords", []):
                if keyword in query_lower:
                    score += 10.0
                elif keyword in query_words:
                    score += 5.0

            # Partial match: +2 points
            for keyword in skill_info.get("keywords", []):
                if len(keyword) > 3 and keyword in query_lower:
                    score += 2.0

            # Priority bonus (core skills get slight boost)
            priority = skill_info.get("priority", 2)
            score += (3 - priority) * 0.5

            if score > 0:
                scores[skill_id] = score

        # Sort by score, return top N
        sorted_skills = sorted(
            scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:max_skills]

        return [
            SkillMatch(
                skill_id=skill_id,
                path=self.manifest["skills"][skill_id]["path"],
                score=score,
                description=self.manifest["skills"][skill_id].get("description", "")
            )
            for skill_id, score in sorted_skills
        ]

    def get_fallback_skills(self) -> list[str]:
        """Return core skills to load if no matches found."""
        return [
            skill_id
            for skill_id, info in self.manifest["skills"].items()
            if info.get("priority") == 1
        ]
```

### 3. ADR Tracer

Ein Tool das ADRs mit ihren Dateien verknüpft:

```python
# src/helix/discovery/adr_tracer.py

@dataclass
class FileTrace:
    """Tracks which ADR created/modified a file."""
    file_path: str
    adr_id: str
    action: str  # "create" | "modify"
    adr_status: str  # "Proposed" | "Implemented" etc.
    file_exists: bool

class ADRTracer:
    """Traces files back to their originating ADRs."""

    def __init__(self, adr_dir: Path, project_root: Path):
        self.adr_dir = adr_dir
        self.project_root = project_root
        self._index: dict[str, FileTrace] = {}
        self._build_index()

    def _build_index(self) -> None:
        """Build file→ADR mapping from all ADR files."""
        for adr_file in self.adr_dir.glob("*.md"):
            if adr_file.name == "INDEX.md":
                continue

            metadata = self._parse_adr_header(adr_file)
            if not metadata:
                continue

            adr_id = metadata.get("adr_id", "")
            status = metadata.get("status", "Unknown")
            files = metadata.get("files", {})

            for file_path in files.get("create", []):
                self._index[file_path] = FileTrace(
                    file_path=file_path,
                    adr_id=adr_id,
                    action="create",
                    adr_status=status,
                    file_exists=(self.project_root / file_path).exists()
                )

            for file_path in files.get("modify", []):
                self._index[file_path] = FileTrace(
                    file_path=file_path,
                    adr_id=adr_id,
                    action="modify",
                    adr_status=status,
                    file_exists=(self.project_root / file_path).exists()
                )

    def trace_file(self, file_path: str) -> FileTrace | None:
        """Find which ADR created/modified a file."""
        return self._index.get(file_path)

    def verify_adr_implementation(self, adr_id: str) -> VerificationResult:
        """
        Check if an ADR is actually implemented.

        Returns:
            VerificationResult with:
            - missing_files: Files that should exist but don't
            - extra_files: Files that exist but aren't in ADR
            - status_mismatch: True if ADR says "Implemented" but files missing
        """
        adr_files = [
            trace for trace in self._index.values()
            if trace.adr_id == adr_id
        ]

        missing = [f for f in adr_files if not f.file_exists]

        # Get ADR status
        adr_path = self.adr_dir / f"{adr_id.zfill(3)}-*.md"
        matches = list(self.adr_dir.glob(f"*{adr_id}*.md"))
        adr_status = "Unknown"
        if matches:
            metadata = self._parse_adr_header(matches[0])
            adr_status = metadata.get("status", "Unknown")

        status_mismatch = (
            adr_status == "Implemented" and len(missing) > 0
        )

        return VerificationResult(
            adr_id=adr_id,
            adr_status=adr_status,
            missing_files=missing,
            status_mismatch=status_mismatch,
            is_complete=len(missing) == 0
        )

    def get_all_traces(self) -> dict[str, FileTrace]:
        """Return the complete file→ADR index."""
        return dict(self._index)
```

### Integration: Consultant Workflow

Der Consultant-Workflow ändert sich:

**Vorher:**
```
1. Lies ALLE skills/*.md
2. Analysiere User-Request
3. Generiere ADR
```

**Nachher:**
```
1. Lade skills/manifest.yaml (klein, ~50 Zeilen)
2. Match User-Request gegen Keywords
3. Lade nur relevante Skills (1-3 Dateien)
4. Generiere ADR
```

**CLAUDE.md Template Update:**

```markdown
## Skill Loading

Bevor du Skills liest:

1. **Lade manifest**: `skills/manifest.yaml`
2. **Match Request**: Analysiere den User-Request gegen Keywords
3. **Lade relevante Skills**: Nur die gematchten Skills lesen

### Keyword Matching

```python
# In deinem Workflow:
from helix.discovery import KeywordMatcher

matcher = KeywordMatcher(Path("skills/manifest.yaml"))
matches = matcher.match("BOM Export für SAP")
# → [SkillMatch(skill_id="pdm", score=15.0),
#    SkillMatch(skill_id="infrastructure", score=10.0)]

for match in matches:
    # Lies nur diese Skills
    read_file(match.path)
```

### Fallback

Wenn keine Keywords matchen, lade Core-Skills:
- `skills/helix/SKILL.md` (immer relevant für HELIX-Entwicklung)
```

## Implementation

### Phase 1: Manifest erstellen

1. Erstelle `skills/manifest.yaml` mit allen existierenden Skills
2. Definiere Keywords für jeden Skill
3. Setze Prioritäten (1=core, 2=domain, 3=tools)

### Phase 2: Discovery-Modul

1. Erstelle `src/helix/discovery/__init__.py`
2. Implementiere `KeywordMatcher` in `keyword_matcher.py`
3. Implementiere `ADRTracer` in `adr_tracer.py`
4. Füge `SkillRegistry` als Fassade hinzu

### Phase 3: Integration

1. Update `docs_compiler.py` um Manifest zu validieren
2. Update CLAUDE.md Template mit Skill-Loading Anweisungen
3. Update Consultant-Phase CLAUDE.md

### Phase 4: CLI Tool

```bash
# Skill Discovery
python -m helix.discovery match "BOM Export für SAP"
# → pdm (score: 15.0)
# → infrastructure (score: 10.0)

# ADR Verification
python -m helix.discovery verify-adr 014
# → ADR-014: Documentation Architecture
# → Status: Proposed
# → Missing files: 0
# → Complete: Yes

# Trace file
python -m helix.discovery trace src/helix/tools/docs_compiler.py
# → ADR-014: Documentation Architecture
# → Action: modify
```

## Dokumentation

| Dokument | Änderung |
|----------|----------|
| `CLAUDE.md` | Skill-Loading Workflow dokumentieren |
| `skills/helix/SKILL.md` | Discovery-Modul dokumentieren |
| `skills/manifest.yaml` | Neue Datei (Self-documenting) |
| `docs/SELF-DOCUMENTATION.md` | Manifest-Maintenance ergänzen |

## Akzeptanzkriterien

### Funktionalität

- [ ] `skills/manifest.yaml` existiert mit allen Skills
- [ ] `KeywordMatcher` findet relevante Skills für Test-Queries
- [ ] `ADRTracer` baut korrekten File→ADR Index
- [ ] CLI-Tool `helix.discovery` funktioniert

### Performance

- [ ] Manifest-Laden < 10ms
- [ ] Keyword-Matching < 50ms für typische Queries
- [ ] ADR-Index Aufbau < 500ms (einmalig pro Session)

### Tests

- [ ] Unit Tests für KeywordMatcher
- [ ] Unit Tests für ADRTracer
- [ ] Integration Test: Consultant findet richtige Skills

### Qualität

- [ ] Fallback zu Core-Skills wenn keine Matches
- [ ] Graceful degradation bei fehlendem Manifest
- [ ] Docstrings und Type Hints vollständig

## Konsequenzen

### Vorteile

1. **Weniger Token-Verbrauch**
   - Statt ~5000 Zeilen nur ~500-1000 pro Session
   - Geschätzte Ersparnis: 80% Token-Kosten für Consultant-Phase

2. **Schnellere Responses**
   - Weniger Kontext = schnellere Verarbeitung
   - Fokussiertere Antworten

3. **ADR-Traceability**
   - Jede Datei ist zu ihrem ADR verfolgbar
   - Status-Inkonsistenzen werden erkannt
   - Besseres Verständnis des Systems

4. **Erweiterbarkeit**
   - Neue Skills einfach durch Manifest-Eintrag
   - Keywords können verfeinert werden
   - Basis für spätere Embedding-Erweiterung

### Nachteile

1. **Maintenance-Overhead**
   - Manifest muss gepflegt werden
   - Keywords müssen aktuell gehalten werden

2. **Mögliche False Negatives**
   - Keyword-Matching kann relevante Skills übersehen
   - Fallback zu Core-Skills als Mitigation

3. **Initiale Lernkurve**
   - Consultants müssen neuen Workflow lernen
   - Aber: Dokumentiert in CLAUDE.md

### Mitigation

- **Manifest-Validation**: Docs-Compiler validiert Manifest gegen existierende Skills
- **Fallback-Strategie**: Core-Skills werden immer geladen wenn Unsicherheit
- **Iterative Keyword-Verbesserung**: Keywords basierend auf Usage-Patterns verfeinern
