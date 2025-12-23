# Aufgabe: CLAUDE.md Migration - Template-Verbesserung

Du bist der HELIX Consultant. Analysiere und verbessere die Dokumentations-Templates.

## Kontext

ADR-014 implementiert generierte Dokumentation:
- YAML Sources in `docs/sources/`
- Jinja2 Templates in `docs/templates/`
- DocCompiler generiert CLAUDE.md und SKILL.md

**Problem:** Die generierte CLAUDE.md hat Gaps gegenüber der manuellen Version.

## Deine Aufgabe

### 1. Gap-Analyse

Vergleiche:
- `../../CLAUDE.md` (manuell, 377 Zeilen)
- `../../generated/CLAUDE.md` (generiert, 354 Zeilen)

Identifiziere:
- Fehlende Sections
- Fehlende Inhalte
- Formatierungsprobleme
- Qualitätsunterschiede

### 2. Lösungs-Entscheidungen

Für jeden Gap entscheide:

| Gap | Option A | Option B | Empfehlung |
|-----|----------|----------|------------|
| Fehlende Section X | In YAML Source | Im Template hardcoden | ? |
| ... | ... | ... | ? |

### 3. Implementation

Erstelle verbesserte Versionen:

**Option A: Neue YAML Source**
```yaml
# docs/sources/consultant-workflow.yaml
workflow:
  questions:
    - "Was genau soll gebaut werden?"
    - "Warum wird das benötigt?"
  templates:
    spec_yaml: |
      name: Feature Name
      ...
```

**Option B: Template-Fix**
```jinja2
{# Hardcoded Section #}
## Klärende Fragen
...
```

### 4. Output

Schreibe nach `output/`:
1. `gap-analysis.md` - Vollständige Analyse
2. `docs/sources/*.yaml` - Neue/erweiterte Sources
3. `docs/templates/*.j2` - Verbesserte Templates
4. `MIGRATION-PLAN.md` - Schritt-für-Schritt Anleitung

## Qualitätskriterien

Nach der Migration soll:
- [ ] Generierte CLAUDE.md >= manuelle Version (Inhalt)
- [ ] Keine Leerzeilen-Probleme
- [ ] Konsistente Sprache (Deutsch)
- [ ] Alle wichtigen Sections vorhanden
- [ ] "Klärende Fragen" mit Templates für spec.yaml/phases.yaml
