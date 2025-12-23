# Aufgabe: Sub-Agent Freigabe-Konzept

Du bist der HELIX Meta-Consultant. Entwickle ein Konzept für Sub-Agenten als Freigabe-Instanzen.

## Die Idee des Users

Statt separater API-Calls für Validierung:

```
Meta-Consultant 
    → Domain-Consultant (HELIX) 
        → Sub-Agent (Freigabe) ← FRISCHER CONTEXT!
```

Der Sub-Agent:
- Wird von der Claude Code CLI Instanz gespawnt
- Hat FRISCHEN Context (keine Kontamination)
- Führt spezifische Freigabe-Prüfungen aus
- Prüfungen sind in einem Verzeichnis definiert (z.B. `approvals/`)

## Warum ist das interessant?

1. **Frischer Context**: Der Prüfer hat keine Voreingenommenheit vom Erstellungsprozess
2. **Separation of Concerns**: Ersteller ≠ Prüfer
3. **Nutzt bestehende Infrastruktur**: Claude Code CLI, keine extra API
4. **Generisch**: Nicht nur für ADRs, sondern für alles

## Deine Aufgabe

Entwickle ein vollständiges Konzept:

### 1. Architektur

Wie spawnt man einen Sub-Agenten?

```bash
# Option A: Neuer claude Prozess
claude -p "Führe Freigabeprüfung aus für: $FILE" --cwd approvals/adr

# Option B: Dediziertes Approval-Projekt
cd approvals/adr && claude -p "Prüfe: $FILE"

# Option C: Approval als HELIX-Phase
# Phase mit type: approval spawnt automatisch Sub-Agent
```

### 2. Approval-Verzeichnis Struktur

```
approvals/
├── adr/
│   ├── CLAUDE.md          # Approval-spezifische Instruktionen
│   ├── checks/
│   │   ├── completeness.md
│   │   ├── migration-plan.md
│   │   └── acceptance-criteria.md
│   └── output/
│       └── approval-result.json
├── code/
│   ├── CLAUDE.md
│   └── checks/
│       ├── security.md
│       ├── performance.md
│       └── tests.md
└── docs/
    └── ...
```

### 3. Workflow-Integration

Wie integriert sich das in HELIX?

```yaml
phases:
  - id: consultant
    type: consultant
    output: [output/ADR-*.md]
    
  - id: approval
    type: approval           # NEU: Spawnt Sub-Agent
    approval_type: adr       # → approvals/adr/
    input: [output/ADR-*.md]
    output: [output/approval-result.json]
```

### 4. Generische Anwendungen

Wo macht Sub-Agent Freigabe noch Sinn?

- ADR-Prüfung (unser aktueller Use Case)
- Code-Review (Security, Performance)
- Dokumentations-Review
- Test-Coverage-Analyse
- Architektur-Konformität
- Compliance-Prüfung

### 5. Vorteile vs. Direkte API

| Aspekt | Direkter API-Call | Sub-Agent |
|--------|-------------------|-----------|
| Context | Kein HELIX-Context | Voller HELIX-Context |
| Tools | Keine | Alle Claude Tools |
| Skills | Keine | Kann Skills laden |
| Kosten | Nur Tokens | Volle Instanz |
| Flexibilität | Starr | Dynamisch |

### 6. Technische Umsetzung

Wie spawnt man konkret?

```python
# helix/approval/runner.py

def spawn_approval_agent(
    approval_type: str,
    files_to_check: list[Path],
) -> ApprovalResult:
    """Spawnt einen Sub-Agenten für Freigabe."""
    
    approval_dir = Path(f"approvals/{approval_type}")
    
    # Kopiere Files in approval input
    for f in files_to_check:
        shutil.copy(f, approval_dir / "input")
    
    # Spawn Sub-Agent
    result = subprocess.run([
        "claude", "-p",
        "Lies CLAUDE.md und führe alle Checks in checks/ aus. "
        "Schreibe das Ergebnis in output/approval-result.json",
        "--dangerously-skip-permissions",
    ], cwd=approval_dir, capture_output=True)
    
    # Parse Ergebnis
    return ApprovalResult.from_json(
        approval_dir / "output/approval-result.json"
    )
```

## Output

Schreibe in output/subagent-approval.md:

1. Konzept-Übersicht (Warum Sub-Agent besser als API-Call)
2. Architektur-Entscheidungen
3. Verzeichnis-Struktur
4. Workflow-Integration (phases.yaml)
5. Technische Implementation
6. Generische Anwendungen (Matrix)
7. Vergleich mit anderen Ansätzen
8. Empfehlung + Roadmap
