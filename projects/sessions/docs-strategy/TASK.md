# Aufgabe: Dokumentations-Strategie für HELIX

Du bist der HELIX Meta-Consultant. Entwickle eine Dokumentations-Strategie.

## Problem

1. **Context Window Limit**: Zu viel Doku = Context voll, Claude kann nicht mehr arbeiten
2. **Konsistenz**: Feature entfernt → Doku muss auch entfernt werden (aus allen Stellen!)
3. **Verteilt**: Doku ist verteilt über docs/, skills/, adr/, CLAUDE.md, README, etc.
4. **Lifecycle**: Bei Refactoring, Revert, Feature-Removal → Doku wird inkonsistent

## Deine Aufgabe

Lies zuerst diese Dateien um den Status Quo zu verstehen:
- ../../CLAUDE.md
- ../../docs/SELF-DOCUMENTATION.md (falls vorhanden)
- ../../skills/helix/SKILL.md
- ../../adr/INDEX.md

Dann entwickle eine Strategie:

### 1. Dokumentations-Hierarchie

Wie strukturieren wir die Doku? Idee:

```
KERN (immer geladen, ~2000 tokens max):
  → CLAUDE.md (Kurzfassung)
  
LAYER 2 (bei Bedarf, lazy loading):
  → Skills, ADRs, Architektur
  
LAYER 3 (selten, nur auf Anfrage):
  → Detaillierte Guides, Historische ADRs
```

### 2. Single Source of Truth

Wo ist die "Bibel"? Vorschläge:
- Ein Master-Index der alle Doku-Stellen listet?
- ADRs als Source of Truth für Architektur?
- Skills als Source of Truth für Domain?

### 3. Konsistenz-Enforcement

Wie stellen wir sicher dass Doku konsistent bleibt?
- Automatische Validierung?
- Zyklisches "Doku-Audit" Projekt?
- Linked References die geprüft werden können?

### 4. Lifecycle Management

Was passiert bei:
- Feature hinzugefügt → Wo muss Doku hin?
- Feature entfernt → Wie finden wir alle Stellen?
- Feature geändert → Wie updaten wir konsistent?

### 5. Tooling

Welche Tools brauchen wir?
- docs_validate.py - Prüft Konsistenz
- docs_audit.py - Findet verwaiste Referenzen
- docs_index.py - Generiert Master-Index

## Output

Schreibe deine Strategie in: output/docs-strategy.md

Format:
1. Analyse des Status Quo
2. Vorgeschlagene Hierarchie (mit Token-Budget)
3. Konsistenz-Regeln
4. Lifecycle-Prozesse
5. Tooling-Vorschläge
6. Empfohlene nächste Schritte

Sei konkret und pragmatisch - was können wir JETZT umsetzen?
