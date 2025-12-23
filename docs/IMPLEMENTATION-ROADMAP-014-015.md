# Implementierungs-Roadmap: ADR-014 & ADR-015

> Empfohlene Reihenfolge für die Umsetzung beider ADRs

---

## Übersicht

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ADR-014: Documentation Architecture                                    │
│  └── Generated Docs, Single Source of Truth, Enforcement               │
├─────────────────────────────────────────────────────────────────────────┤
│  ADR-015: Approval & Validation System                                  │
│  └── Hybrid Pre-Checks + Sub-Agent für unabhängige Prüfung             │
└─────────────────────────────────────────────────────────────────────────┘
```

## Abhängigkeiten

```
ADR-014                              ADR-015
   │                                    │
   │  UNABHÄNGIG                        │  UNABHÄNGIG
   │  ──────────                        │  ──────────
   │  docs/sources/                     │  approvals/
   │  docs/templates/                   │  completeness.py
   │  docs_compiler.py                  │  concept_diff.py
   │                                    │  ApprovalRunner
   │                                    │
   └──────────────┬─────────────────────┘
                  │
                  │  SYNERGIE
                  │  ────────
                  │  docs_compiled als Quality Gate
                  │  docstrings_complete als Approval-Check
                  │  Sub-Agent kann Doku validieren
```

---

## Empfohlene Reihenfolge

### Woche 1: ADR-015 Foundation

| Tag | Task | Output |
|-----|------|--------|
| 1-2 | Completeness Rules Engine | `config/adr-completeness-rules.yaml`, `completeness.py` |
| 3 | Concept Diff | `concept_diff.py` |
| 4-5 | Unit Tests | Tests für Layer 2-3 |

**Warum zuerst?** Die Pre-Checks (Layer 1-3) sind die Basis für alle Validierungen.

### Woche 2: ADR-015 Sub-Agent

| Tag | Task | Output |
|-----|------|--------|
| 1-2 | ApprovalRunner + Result | `src/helix/approval/` |
| 3-4 | ADR Approval Setup | `approvals/adr/CLAUDE.md`, `checks/*.md` |
| 5 | E2E Test | ADR → Pre-Check → Sub-Agent → Result |

**Milestone:** Erster funktionierender Approval-Workflow

### Woche 3: Quality Gates + ADR-014 Start

| Tag | Task | Output |
|-----|------|--------|
| 1-2 | adr_complete Gate | Integration in QualityGateRunner |
| 3 | on_rejection Handler | Retry-Logik |
| 4-5 | ADR-014: docs/sources/ | `quality-gates.yaml`, `phase-types.yaml` |

**Milestone:** ADRs werden automatisch geprüft, Doku-Sources existieren

### Woche 4: ADR-014 Compiler + Integration

| Tag | Task | Output |
|-----|------|--------|
| 1-3 | docs_compiler.py | Kompilierung funktioniert |
| 4 | Templates | `CLAUDE.md.j2`, `SKILL.md.j2` |
| 5 | Integration Test | Generierte Docs = Erwartung |

**Milestone:** Dokumentation wird generiert

### Woche 5: Enforcement + Cleanup

| Tag | Task | Output |
|-----|------|--------|
| 1-2 | docs_compiled Gate | Quality Gate für Doku |
| 3 | Pre-Commit Hook | Automatische Validierung |
| 4-5 | Migration | Bestehende Docs → generierte Version |

**Milestone:** Beide Systeme produktionsreif

---

## Quick Start (Tag 1)

```bash
# 1. Verzeichnisse erstellen
mkdir -p approvals/adr/checks
mkdir -p config
mkdir -p docs/sources docs/templates/partials

# 2. Erste Regel-Datei
cat > config/adr-completeness-rules.yaml << 'YAML'
contextual_rules:
  - id: major-needs-migration
    name: "Major Changes erfordern Migrationsplan"
    when:
      change_scope: major
    require:
      sections:
        - name: "Migration"
          min_length: 100
    severity: error
    message: "change_scope=major erfordert einen Migrations-Plan"
YAML

# 3. Erste Approval CLAUDE.md
cat > approvals/adr/CLAUDE.md << 'MD'
# ADR Approval Agent

Du prüfst ADRs auf Vollständigkeit und Qualität.

## Input
- input/ADR-*.md - Das zu prüfende ADR
- input/precheck-result.json - Ergebnisse der Pre-Checks

## Aufgabe
1. Lies das ADR vollständig
2. Prüfe inhaltliche Vollständigkeit
3. Verifiziere Referenzen (nutze Read/Grep)
4. Schreibe output/approval-result.json
MD

echo "✅ Basis-Struktur erstellt"
```

---

## Metriken

| Metrik | Ziel | Messung |
|--------|------|---------|
| Pre-Check Latenz | < 1s | Time per validation |
| Sub-Agent Latenz | < 60s | Time per approval |
| Sub-Agent Kosten | < $0.30 | Tokens per approval |
| False Positives | < 5% | Manual review |
| Caught Issues | > 90% | Issues found / total issues |

---

## Risiken

| Risiko | Mitigation |
|--------|------------|
| Sub-Agent zu langsam | Timeout + Caching |
| Sub-Agent zu teuer | Nur bei major/critical |
| False Positives nerven | Severity-Tuning |
| Regeln zu strikt | Warning statt Error |

---

## Referenzen

- ADR-014: `adr/014-documentation-architecture.md`
- ADR-015: `adr/015-approval-validation-system.md`
- Konzept Docs: `projects/sessions/docs-architecture/output/`
- Konzept Approval: `projects/sessions/subagent-approval/output/`
- Konzept Completeness: `projects/sessions/adr-completeness/output/`

