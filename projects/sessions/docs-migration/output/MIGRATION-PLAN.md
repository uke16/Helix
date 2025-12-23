# Migration Plan: CLAUDE.md Template-Verbesserung

## Übersicht

Dieses Dokument beschreibt die Schritte um die verbesserten Templates und Sources in HELIX v4 zu integrieren.

---

## Phase 1: Sources installieren

### Schritt 1.1: Neue Sources kopieren

```bash
# Von output/ nach docs/sources/
cp output/docs/sources/consultant-workflow.yaml ../../docs/sources/
cp output/docs/sources/evolution.yaml ../../docs/sources/
cp output/docs/sources/tools.yaml ../../docs/sources/
```

### Schritt 1.2: Sources validieren

```bash
# YAML Syntax prüfen
python -c "import yaml; yaml.safe_load(open('docs/sources/consultant-workflow.yaml'))"
python -c "import yaml; yaml.safe_load(open('docs/sources/evolution.yaml'))"
python -c "import yaml; yaml.safe_load(open('docs/sources/tools.yaml'))"
```

---

## Phase 2: Template installieren

### Schritt 2.1: Altes Template sichern

```bash
cp docs/templates/CLAUDE.md.j2 docs/templates/CLAUDE.md.j2.bak
```

### Schritt 2.2: Neues Template kopieren

```bash
cp output/docs/templates/CLAUDE.md.j2 ../../docs/templates/
```

---

## Phase 3: DocsCompiler erweitern

### Schritt 3.1: Neue Sources im Compiler registrieren

Der `DocsCompiler` muss die neuen Sources laden. Datei: `src/helix/tools/docs_compiler.py`

```python
# In der load_sources() Methode hinzufügen:

def load_sources(self) -> dict:
    sources = {}
    source_files = [
        'docs/sources/quality-gates.yaml',
        'docs/sources/phase-types.yaml',
        'docs/sources/domains.yaml',
        'docs/sources/escalation.yaml',
        # NEU:
        'docs/sources/consultant-workflow.yaml',
        'docs/sources/evolution.yaml',
        'docs/sources/tools.yaml',
    ]

    for source_file in source_files:
        if Path(source_file).exists():
            with open(source_file) as f:
                name = Path(source_file).stem.replace('-', '_')
                sources[name] = yaml.safe_load(f)

    return sources
```

### Schritt 3.2: Template-Kontext erweitern

```python
def get_template_context(self) -> dict:
    sources = self.load_sources()
    return {
        'quality_gates': sources.get('quality_gates'),
        'phase_types': sources.get('phase_types'),
        'domains': sources.get('domains'),
        'escalation': sources.get('escalation'),
        # NEU:
        'consultant_workflow': sources.get('consultant_workflow'),
        'evolution': sources.get('evolution'),
        'tools': sources.get('tools'),
    }
```

---

## Phase 4: Generierung testen

### Schritt 4.1: Diff prüfen

```bash
python -m helix.tools.docs_compiler diff
```

### Schritt 4.2: Erwartete Änderungen

Die generierte CLAUDE.md sollte nun enthalten:

| Section | Vorher | Nachher |
|---------|--------|---------|
| Consultant Fragen-Schema | ❌ Fehlt | ✅ Vorhanden |
| spec.yaml/phases.yaml Templates | ❌ Fehlt | ✅ Vorhanden |
| Evolution API | ❌ Fehlt | ✅ Vorhanden |
| Safety Guarantees | ❌ Fehlt | ✅ Vorhanden |
| Tool Python API | ❌ Fehlt | ✅ Vorhanden |
| Checkboxen bei DO/DON'T | ❌ Fehlt | ✅ Vorhanden |
| Unicode Pfeile (→) | ❌ ASCII (->) | ✅ Unicode (→) |
| Leerzeilen | ❌ Zu viele | ✅ Bereinigt |

### Schritt 4.3: Kompilieren

```bash
python -m helix.tools.docs_compiler compile
```

### Schritt 4.4: Manuelle Prüfung

```bash
# Zeilenanzahl vergleichen
wc -l CLAUDE.md generated/CLAUDE.md

# Diff zur manuellen Version
diff CLAUDE.md generated/CLAUDE.md
```

---

## Phase 5: Integration

### Schritt 5.1: Generierte Version aktivieren

Wenn die generierte Version >= manuelle Version:

```bash
# Backup
cp CLAUDE.md CLAUDE.md.manual.bak

# Aktivieren
cp generated/CLAUDE.md CLAUDE.md
```

### Schritt 5.2: Manuelle Version entfernen

Nach erfolgreicher Validierung kann die manuelle CLAUDE.md entfernt werden:

```bash
git rm CLAUDE.md.manual.bak
```

---

## Validierung

### Checkliste

- [ ] Alle Sources laden ohne Fehler
- [ ] Template rendert ohne Fehler
- [ ] Generierte CLAUDE.md hat alle Sections der manuellen Version
- [ ] Keine doppelten Leerzeilen
- [ ] Unicode-Pfeile (→) statt ASCII (->)
- [ ] Checkboxen bei DO/DON'T (✅/❌)
- [ ] Consultant Fragen-Schema vorhanden
- [ ] spec.yaml/phases.yaml Templates vorhanden
- [ ] Evolution API mit curl-Beispielen
- [ ] Safety Guarantees Liste
- [ ] Tool Python API Beispiele
- [ ] Projekt-Struktur mit Phasen-Details

### Automatischer Test

```python
# test_claude_md_quality.py
def test_generated_claude_md_has_all_sections():
    with open('generated/CLAUDE.md') as f:
        content = f.read()

    required_sections = [
        '## Projekt verstehen',
        '## Wichtige Dateien zuerst lesen',
        '## Output-Regeln',
        '## Quality Gates Reference',
        '## Projekt-Struktur',
        '## Consultant-Rolle',
        '### Fragen-Schema',
        '### Output generieren',
        '## Developer-Rolle',
        '## Wichtige Hinweise',
        '## Evolution Projects',
        '### Evolution API',
        '### Safety Guarantees',
        '## Self-Documentation Prinzip',
        '## Available Tools',
    ]

    for section in required_sections:
        assert section in content, f"Missing section: {section}"

def test_no_double_blank_lines():
    with open('generated/CLAUDE.md') as f:
        content = f.read()

    assert '\n\n\n' not in content, "Double blank lines found"

def test_unicode_arrows():
    with open('generated/CLAUDE.md') as f:
        content = f.read()

    # Sollte → haben, nicht ->
    assert '→' in content, "Missing unicode arrows"
```

---

## Rollback

Falls Probleme auftreten:

```bash
# Template zurücksetzen
cp docs/templates/CLAUDE.md.j2.bak docs/templates/CLAUDE.md.j2

# Sources entfernen
rm docs/sources/consultant-workflow.yaml
rm docs/sources/evolution.yaml
rm docs/sources/tools.yaml

# Manuelle Version wiederherstellen
git checkout CLAUDE.md
```

---

## Dateien in diesem Output

| Datei | Beschreibung |
|-------|--------------|
| `gap-analysis.md` | Vollständige Gap-Analyse |
| `docs/sources/consultant-workflow.yaml` | Consultant Workflow Source |
| `docs/sources/evolution.yaml` | Evolution System Source |
| `docs/sources/tools.yaml` | Tool Documentation Source |
| `docs/templates/CLAUDE.md.j2` | Verbessertes Template |
| `MIGRATION-PLAN.md` | Diese Anleitung |
