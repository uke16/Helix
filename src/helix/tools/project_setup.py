"""Project Setup Tool for HELIX v4.

Creates new projects with correct directory structure and templates.

Usage:
    python -m helix.tools.project_setup create consultant-adr-021 --type adr
    python -m helix.tools.project_setup create my-feature --type feature
"""

import argparse
from datetime import datetime
from pathlib import Path

import yaml


def create_adr_project(name: str, base_dir: Path, adr_id: str = None) -> Path:
    """Create a new ADR project with Consultant setup."""
    project_dir = base_dir / name
    project_dir.mkdir(parents=True, exist_ok=True)
    
    # Create CORRECT structure: phases/1/input, phases/1/output
    phase_dir = project_dir / "phases" / "1"
    phase_dir.mkdir(parents=True, exist_ok=True)
    (phase_dir / "input").mkdir(exist_ok=True)
    (phase_dir / "output").mkdir(exist_ok=True)
    
    # Determine next ADR ID if not provided
    if adr_id is None:
        adr_dir = Path("adr")
        existing = [f.stem.split("-")[0] for f in adr_dir.glob("*.md") if f.stem[0].isdigit()]
        next_id = max([int(x) for x in existing if x.isdigit()] + [0]) + 1
        adr_id = f"{next_id:03d}"
    
    # Create phases.yaml
    phases_yaml = {
        "project_type": "adr_creation",
        "name": f"ADR-{adr_id} Creation",
        "phases": [{
            "id": "1",
            "name": "Consultant Meeting",
            "type": "consultant",
            "input": ["input/request.md"],
            "output": ["output/ADR-draft.md"],
            "quality_gates": [
                {"type": "files_exist", "files": ["output/ADR-draft.md"]},
                {"type": "adr_valid", "file": "output/ADR-draft.md"}
            ]
        }],
        "skills": ["helix", "helix/adr"]
    }
    
    with open(project_dir / "phases.yaml", "w") as f:
        yaml.dump(phases_yaml, f, default_flow_style=False, allow_unicode=True)
    
    # Create CLAUDE.md IN PHASE DIRECTORY (not project root!)
    claude_md = f'''# Consultant Phase - ADR Creation

Du bist ein Consultant der ein neues ADR (Architecture Decision Record) erstellt.

## Deine Aufgabe

1. **Lies input/request.md** - Verstehe das Problem
2. **Lies relevante Skills** - skills/helix/SKILL.md, skills/helix/adr/SKILL.md
3. **Analysiere das bestehende System** - Schau dir relevante Dateien an
4. **Entwickle eine Lösung** - Denke eigenständig nach:
   - Welche Architektur löst das Problem?
   - Wie funktioniert das stabil und zuverlässig?
   - Was sind die Edge Cases?
5. **Erstelle output/ADR-draft.md** - Im korrekten ADR-Format
6. **VALIDIERE SELBST** - Rufe das Validation Tool auf bevor du fertig bist

## WICHTIG: Selbst-Validierung

Nach dem Erstellen des ADR, führe aus:

```bash
cd $HELIX_ROOT  # or the path to your HELIX installation
PYTHONPATH=src python3 -m helix.tools.adr_tool validate {phase_dir}/output/ADR-draft.md
```

**Bei Errors:** Korrigiere das ADR und validiere erneut!

## Reflexions-Fragen

Bevor du das ADR finalisierst:

1. **Stabilität:** Wie funktioniert die Lösung bei Edge-Cases?
2. **Fallback:** Was passiert wenn die Haupt-Logik fehlschlägt?
3. **Integration:** Passt die Lösung zum bestehenden System?
4. **Alternativen:** Welche anderen Ansätze hast du erwogen?

## ADR Format

```yaml
---
adr_id: "{adr_id}"
title: "Dein Titel"
status: Proposed
date: {datetime.now().strftime("%Y-%m-%d")}
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
    - pfad/zu/datei.py
  modify:
    - existierende/datei.py
  docs:
    - skills/helix/SKILL.md
depends_on:
  - "014"
---
```

Pflicht-Sections: Kontext, Entscheidung, Implementation, Dokumentation, Akzeptanzkriterien, Konsequenzen
'''
    
    # Write CLAUDE.md to PHASE directory
    (phase_dir / "CLAUDE.md").write_text(claude_md)
    
    # Create template request.md IN PHASE INPUT DIRECTORY
    request_template = '''# Problem: [Beschreibe das Problem]

[Was ist das Problem?]

**Beispiel:**
```
[Konkretes Beispiel]
```

**Constraints:**
- [Constraint 1]
- [Constraint 2]
'''
    
    (phase_dir / "input" / "request.md").write_text(request_template)
    
    print(f"✅ ADR Project created: {project_dir}")
    print(f"   ADR ID: {adr_id}")
    print(f"   Structure:")
    print(f"   {project_dir}/")
    print(f"   ├── phases.yaml")
    print(f"   └── phases/1/")
    print(f"       ├── CLAUDE.md")
    print(f"       ├── input/request.md")
    print(f"       └── output/")
    print(f"")
    print(f"   Next steps:")
    print(f"   1. Edit {phase_dir}/input/request.md")
    print(f"   2. Run: helix run {project_dir}")
    
    return project_dir


def main():
    parser = argparse.ArgumentParser(description="HELIX Project Setup")
    parser.add_argument("action", choices=["create"])
    parser.add_argument("name", help="Project name")
    parser.add_argument("--type", choices=["adr", "feature"], default="adr")
    parser.add_argument("--base-dir", default="projects", help="Base directory")
    parser.add_argument("--adr-id", help="ADR ID (auto-detected if not provided)")
    
    args = parser.parse_args()
    
    base_dir = Path(args.base_dir)
    
    if args.action == "create":
        if args.type == "adr":
            create_adr_project(args.name, base_dir, args.adr_id)
        else:
            print(f"Type {args.type} not yet implemented")


if __name__ == "__main__":
    main()
