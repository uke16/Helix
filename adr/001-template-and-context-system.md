# ADR-001: Template & Context System

**Status:** Proposed  
**Datum:** 2025-12-21  
**Bezug:** ADR-000  
**Ersetzt:** ADR-001 (SDK Integration) - SDK nicht mehr nötig!

---

## Kontext

HELIX v4 nutzt Claude Code's natives `CLAUDE.md` Feature. 
Dieses ADR definiert wie wir Templates und Context für verschiedene 
Rollen und Sprachen verwalten.

---

## Entscheidung

### 1. Template-Hierarchie

```
templates/
├── base/
│   └── common.md              # Gemeinsame Regeln für alle Agents
│
├── consultant/
│   ├── _base.md               # Basis-Consultant Template
│   ├── pdm.md                 # PDM Domain Spezialisierung
│   ├── erp.md                 # ERP Domain Spezialisierung
│   └── generic.md             # Fallback
│
├── developer/
│   ├── _base.md               # Basis-Developer Template
│   ├── python.md              # Python Spezialisierung
│   ├── cpp.md                 # C++ Spezialisierung
│   ├── go.md                  # Go Spezialisierung
│   ├── typescript.md          # TypeScript Spezialisierung
│   ├── rust.md                # Rust Spezialisierung
│   └── deploy.md              # DevOps/Infrastructure
│
├── reviewer/
│   ├── _base.md               # Basis-Reviewer Template
│   ├── code.md                # Code Quality Review
│   ├── security.md            # Security Review
│   └── architecture.md        # Architecture Review
│
└── documentation/
    ├── _base.md               # Basis-Docs Template
    ├── api.md                 # API Dokumentation
    ├── user.md                # User-facing Docs
    └── technical.md           # Technical/Architecture Docs
```

### 2. Template-Format (Jinja2)

```markdown
{# templates/developer/python.md #}

{% extends "_base.md" %}

{% block role %}
Du bist ein erfahrener Python Developer.
{% endblock %}

{% block language_rules %}
## Python-spezifische Regeln

1. **Typing**: Alle Funktionen haben Type Hints
2. **Docstrings**: Google-Style Docstrings
3. **Tests**: pytest mit fixtures
4. **Linting**: Code muss PEP 8 konform sein
5. **Imports**: Sortiert mit isort-Konvention
{% endblock %}

{% block tools %}
- `python3` für Ausführung
- `pytest` für Tests
- `mypy` für Type Checking (optional)
{% endblock %}
```

```markdown
{# templates/developer/_base.md #}

# Developer

{% block role %}
Du bist Developer für HELIX.
{% endblock %}

## Deine Aufgabe

{{ summary }}

## Zu erstellende Dateien

{% for file in files_to_create %}
### `{{ file.path }}`
{{ file.description }}

{% endfor %}

## Zu modifizierende Dateien

{% for file in files_to_modify %}
- `{{ file.path }}`: {{ file.change }}
{% endfor %}

## Akzeptanzkriterien

{% for criterion in acceptance_criteria %}
- [ ] {{ criterion }}
{% endfor %}

{% block language_rules %}
{# Wird von Spezialisierung überschrieben #}
{% endblock %}

## Verfügbare Skills

Lies diese Dateien für Best Practices:

{% for skill in skills %}
- `skills/{{ skill }}`
{% endfor %}

{% block tools %}
{# Wird von Spezialisierung überschrieben #}
{% endblock %}

## Output

Wenn du fertig bist, erstelle `logs/result.json`:

```json
{
  "status": "completed",
  "files_created": [...],
  "files_modified": [...],
  "tests_passed": true,
  "notes": "..."
}
```
```

### 3. Skill-Bibliothek

```
skills/
├── languages/
│   ├── python/
│   │   ├── patterns.md        # Design Patterns
│   │   ├── testing.md         # pytest, fixtures, mocking
│   │   ├── typing.md          # Type Hints Best Practices
│   │   ├── async.md           # asyncio Patterns
│   │   └── packaging.md       # pyproject.toml, etc.
│   │
│   ├── cpp/
│   │   ├── modern.md          # C++17/20 Features
│   │   ├── cmake.md           # CMake Best Practices
│   │   ├── testing.md         # Catch2, GoogleTest
│   │   └── memory.md          # RAII, Smart Pointers
│   │
│   └── go/
│       ├── idioms.md          # Go Idioms
│       ├── testing.md         # go test
│       └── concurrency.md     # Goroutines, Channels
│
├── tools/
│   ├── git.md                 # Git Workflows
│   ├── docker.md              # Dockerfile Best Practices
│   ├── kubernetes.md          # K8s Manifests
│   └── ci-cd.md               # GitHub Actions, etc.
│
├── domains/
│   ├── pdm/
│   │   ├── structure.md       # PDM Datenstruktur
│   │   ├── bom.md             # Stücklisten
│   │   ├── revisions.md       # Revisions-System
│   │   └── workflows.md       # PDM Workflows
│   │
│   └── erp/
│       ├── integration.md     # ERP Integration
│       └── data-models.md     # ERP Datenmodelle
│
└── helix/
    ├── conventions.md         # HELIX Coding Conventions
    ├── testing.md             # HELIX Test Patterns
    └── architecture.md        # HELIX Architecture Overview
```

### 4. Context-Preparation

```python
# context_manager.py

from pathlib import Path
from typing import Optional

class ContextManager:
    """Verwaltet Context/Skills für Claude Code Phasen."""
    
    def __init__(self, helix_root: Path):
        self.helix_root = helix_root
        self.skills_dir = helix_root / "skills"
        self.templates_dir = helix_root / "templates"
    
    def get_skills_for_language(self, language: str) -> list[Path]:
        """Gibt relevante Skills für eine Programmiersprache zurück."""
        
        base_skills = [
            self.skills_dir / "tools" / "git.md",
        ]
        
        language_dir = self.skills_dir / "languages" / language
        if language_dir.exists():
            base_skills.extend(language_dir.glob("*.md"))
        
        return base_skills
    
    def get_skills_for_domain(self, domain: str) -> list[Path]:
        """Gibt relevante Skills für eine Domain zurück."""
        
        domain_dir = self.skills_dir / "domains" / domain
        if domain_dir.exists():
            return list(domain_dir.glob("*.md"))
        return []
    
    def prepare_phase_context(
        self, 
        phase_dir: Path, 
        language: Optional[str] = None,
        domain: Optional[str] = None,
        additional_skills: list[str] = None
    ):
        """Bereitet Context-Verzeichnis mit Symlinks vor."""
        
        context_dir = phase_dir / "skills"
        context_dir.mkdir(exist_ok=True)
        
        skills = []
        
        if language:
            skills.extend(self.get_skills_for_language(language))
        
        if domain:
            skills.extend(self.get_skills_for_domain(domain))
        
        if additional_skills:
            for skill_path in additional_skills:
                skill_file = self.skills_dir / skill_path
                if skill_file.exists():
                    skills.append(skill_file)
        
        # Symlinks erstellen
        for skill in skills:
            link_name = f"{skill.parent.name}-{skill.name}"
            link_path = context_dir / link_name
            if not link_path.exists():
                link_path.symlink_to(skill)
        
        return [s.name for s in skills]
```

### 5. Spec → Template Mapping

```python
# template_engine.py

class TemplateEngine:
    """Generiert CLAUDE.md aus Spec und Templates."""
    
    LANGUAGE_DETECTION = {
        ".py": "python",
        ".cpp": "cpp",
        ".cc": "cpp",
        ".h": "cpp",
        ".go": "go",
        ".ts": "typescript",
        ".js": "typescript",  # Gleiche Patterns
        ".rs": "rust",
    }
    
    def detect_language(self, spec: dict) -> str:
        """Erkennt Sprache aus Spec."""
        
        # Explizit in Spec?
        if "language" in spec.get("meta", {}):
            return spec["meta"]["language"]
        
        # Aus Dateiendungen ableiten
        files = spec.get("implementation", {}).get("files_to_create", [])
        extensions = set()
        
        for f in files:
            path = f if isinstance(f, str) else f.get("path", "")
            ext = Path(path).suffix
            if ext:
                extensions.add(ext)
        
        # Häufigste Extension
        for ext in extensions:
            if ext in self.LANGUAGE_DETECTION:
                return self.LANGUAGE_DETECTION[ext]
        
        return "generic"
    
    def detect_role(self, spec: dict) -> str:
        """Erkennt welche Art von Developer gebraucht wird."""
        
        files = spec.get("implementation", {}).get("files_to_create", [])
        
        # Deploy-Indikatoren
        deploy_patterns = ["Dockerfile", "docker-compose", "k8s", ".yaml", "terraform"]
        for f in files:
            path = f if isinstance(f, str) else f.get("path", "")
            if any(p in path for p in deploy_patterns):
                return "deploy"
        
        return "developer"
    
    def generate_claude_md(
        self, 
        phase: str, 
        spec: dict,
        template_override: str = None
    ) -> str:
        """Generiert CLAUDE.md für eine Phase."""
        
        if phase == "consultant":
            domain = spec.get("meta", {}).get("domain", "generic")
            template_name = template_override or f"consultant/{domain}"
        
        elif phase == "developer":
            if template_override:
                template_name = template_override
            else:
                role = self.detect_role(spec)
                if role == "deploy":
                    template_name = "developer/deploy"
                else:
                    language = self.detect_language(spec)
                    template_name = f"developer/{language}"
        
        elif phase == "reviewer":
            template_name = template_override or "reviewer/code"
        
        elif phase == "documentation":
            template_name = template_override or "documentation/technical"
        
        else:
            raise ValueError(f"Unknown phase: {phase}")
        
        return self.render(
            template_name,
            **self._prepare_context(spec)
        )
    
    def _prepare_context(self, spec: dict) -> dict:
        """Bereitet Template-Context aus Spec vor."""
        
        impl = spec.get("implementation", {})
        
        return {
            "summary": impl.get("summary", ""),
            "files_to_create": impl.get("files_to_create", []),
            "files_to_modify": impl.get("files_to_modify", []),
            "acceptance_criteria": impl.get("acceptance_criteria", []),
            "context_docs": spec.get("context", {}).get("relevant_docs", []),
            "domain": spec.get("meta", {}).get("domain", ""),
            "language": self.detect_language(spec),
        }
```

---

## Beispiel: Vollständiger Flow

### 1. Spec von Consultant

```yaml
# spec.yaml
meta:
  domain: "pdm"
  language: "python"

implementation:
  summary: "BOM Export nach CSV mit Revision-History"
  files_to_create:
    - path: "src/exporters/bom_csv.py"
      description: "Hauptmodul für BOM-Export"
    - path: "tests/test_bom_csv.py"
      description: "Unit Tests"
  acceptance_criteria:
    - "CSV enthält alle BOM-Felder"
    - "Revision-History ist enthalten"
    - "Tests sind grün"
```

### 2. Generiertes CLAUDE.md für Developer

```markdown
# Developer

Du bist ein erfahrener Python Developer.

## Deine Aufgabe

BOM Export nach CSV mit Revision-History

## Zu erstellende Dateien

### `src/exporters/bom_csv.py`
Hauptmodul für BOM-Export

### `tests/test_bom_csv.py`
Unit Tests

## Akzeptanzkriterien

- [ ] CSV enthält alle BOM-Felder
- [ ] Revision-History ist enthalten
- [ ] Tests sind grün

## Python-spezifische Regeln

1. **Typing**: Alle Funktionen haben Type Hints
2. **Docstrings**: Google-Style Docstrings
3. **Tests**: pytest mit fixtures

## Verfügbare Skills

- `skills/python-patterns.md`
- `skills/python-testing.md`
- `skills/pdm-bom.md`

## Output

Wenn du fertig bist, erstelle `logs/result.json`:
...
```

---

## Konsequenzen

### Positiv
- **Wiederverwendbar**: Templates für alle Sprachen/Domains
- **Erweiterbar**: Neue Sprache = neues Template + Skills
- **Debuggbar**: Generiertes CLAUDE.md ist lesbar
- **Versionierbar**: Templates in Git

### Negativ
- Template-Pflege nötig
- Jinja2 Dependency

---

## Referenzen

- ADR-000: Vision & Architecture
- HELIX v3 ADR-067: Pre-loaded Context System

