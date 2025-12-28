# ADR-027 finalisiert

Der **Stale Response Bugfix** wurde erfolgreich finalisiert!

---

## Was wurde gemacht

| Schritt | Status |
|---------|--------|
| ADR validiert | Korrektur: `component_type: FIX` → `SERVICE` |
| ADR finalisiert | Verschoben nach `adr/` |
| INDEX.md aktualisiert | Neue Sektion "Bugfixes (027+)" hinzugefügt |
| Status aktualisiert | `Proposed` → `Implemented` |

---

## Ergebnis

**Pfad:** `adr/027-stale-response-bugfix---open-webui-integration.md`

**Status:** Implemented

**Im INDEX.md:**
```
### Bugfixes (027+)
| 027 | Stale Response Bugfix | Implemented | Fix für veraltete Antworten nach Timeout/Error |
```

**Nächste freie ADR-Nummer:** 028

---

## Zusammenfassung

Der ADR-027 dokumentiert den Fix für das Problem, dass Open WebUI nach einem Timeout immer wieder die gleiche alte Antwort gezeigt hat. Die 3 Bugs waren:

1. **Alte response.md bleibt liegen** → Wird jetzt vor Start gelöscht
2. **Keine Timestamp-Validierung** → Jetzt prüft HELIX ob die Datei nach dem Start geschrieben wurde
3. **Kein Error-Handling** → Bei Timeout/Error wird jetzt eine klare Fehlermeldung gesendet

Der Fix ist bereits im Code (`src/helix/api/routes/openai.py`) und jetzt auch offiziell dokumentiert.
