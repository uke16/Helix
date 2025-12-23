# Aufgabe: Review der aktuellen Änderungen

Du bist der HELIX Meta-Consultant.

## Kontext

Wir haben gerade folgende Änderungen implementiert (OHNE ein ADR dafür zu schreiben):

### Änderung 1: Conversational ADR Flow (commit e622b21)

**Was wurde gemacht:**
- Session Manager: Trigger-Erkennung für "mach ein ADR draus", "finalisiere", etc.
- Consultant Template: Neuer `finalize` Step mit Anweisungen für ADR-Erstellung
- API: helix_root zum Template-Context hinzugefügt

**Zweck:**
User kann mit Consultant chatten und am Ende sagen "mach ein ADR draus".
Der Consultant erstellt dann das ADR, validiert es, und finalisiert es automatisch.

### Änderung 2: Template MUST READ erweitert (gerade eben)

**Was wurde gemacht:**
- adr/INDEX.md als PFLICHT hinzugefügt
- skills/helix/adr/SKILL.md als PFLICHT hinzugefügt
- skills/helix/evolution/SKILL.md hinzugefügt

## Deine Aufgaben

Lies zuerst:
- ../../adr/INDEX.md (bestehende ADRs)
- ../../skills/helix/adr/SKILL.md (wann braucht man ein ADR?)

Dann beantworte:

1. **Brauchen wir ein ADR für den Conversational ADR Flow?**
   - Ist das eine "wichtige Architektur-Entscheidung"?
   - Oder ist das nur ein Minor Feature?

2. **Was sollten wir dokumentieren?**
   - Welche Docs sollten aktualisiert werden?
   - Fehlt etwas?

3. **Deine Empfehlung**
   - ADR erstellen: Ja/Nein + Begründung
   - Dokumentation: Was genau aktualisieren?

Schreibe deine Antwort in output/review.md
