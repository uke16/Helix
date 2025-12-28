# ADR-030 Entwurf erstellt

## Korrektur zur ADR-Nummer

Die nächste freie ADR-Nummer ist **030**, nicht 031. Die höchste existierende ADR ist 029 (Open WebUI Session Persistence).

---

## Übersicht

Der ADR-Entwurf wurde erstellt: **`output/ADR-030.md`**

### ADR-030: Evolution Pipeline Reliability

**Status:** Proposed
**Typ:** FIX (helix_internal)
**Scope:** minor

---

## Addressierte Issues

| # | Issue | Lösung |
|---|-------|--------|
| 1 | pytest PATH (exit 127) | Shell-Environment Setup im ClaudeRunner mit virtualenv PATH |
| 2 | Job Status API ohne Phasen | Phasen-Synchronisation in JobState während Ausführung |
| 3 | StrEnum Python 3.10 | Backport-Klasse für Python < 3.11 |
| 4 | Keine Retry bei Fehlern | RetryHandler mit Exponential Backoff für transiente Fehler |

---

## Betroffene Dateien

### Neu erstellen:
- `src/helix/pipeline/retry_handler.py`
- `tests/pipeline/test_retry_handler.py`

### Modifizieren:
- `src/helix/claude_runner.py` (PATH Fix)
- `src/helix/api/streaming.py` (JobState Sync + Retry)
- `src/helix/api/routes.py` (Phasen in Response)
- `src/helix/phase_status.py` (StrEnum Backport)

### Dokumentation:
- `docs/ARCHITECTURE-MODULES.md`

---

## Akzeptanzkriterien

Der ADR enthält **18 überprüfbare Akzeptanzkriterien** mit Checkboxen, gruppiert nach:

1. **Fix 1: pytest PATH** (3 Kriterien)
2. **Fix 2: Job Status API** (4 Kriterien)
3. **Fix 3: StrEnum Kompatibilität** (3 Kriterien)
4. **Fix 4: Retry Handler** (5 Kriterien)
5. **Integration** (3 Kriterien)

---

## Validierung

Das ADR wurde manuell validiert (Python-Umgebung unvollständig):

- YAML-Header: Alle Pflicht- und empfohlenen Felder vorhanden
- Markdown-Body: Alle 6 Pflicht-Sections vorhanden
- Akzeptanzkriterien: 18 Checkboxen (Minimum: 3)

---

## Nächste Schritte

1. **Review:** ADR-Entwurf durchlesen und ggf. anpassen
2. **Finalisieren:** ADR nach `adr/030-evolution-pipeline-reliability.md` verschieben
3. **INDEX.md:** ADR-Index aktualisieren
4. **Implementation:** phases.yaml für Umsetzung erstellen

### Finalisieren (manuell):

```bash
cp output/ADR-030.md /home/aiuser01/helix-v4/adr/030-evolution-pipeline-reliability.md
```

Dann INDEX.md aktualisieren mit:

```markdown
| 030 | [Evolution Pipeline Reliability](030-evolution-pipeline-reliability.md) | 📋 | pytest PATH, Job API, StrEnum, Retry |
```

---

## Fragen?

Falls du Änderungen am ADR-Entwurf wünschst:
- Andere Priorisierung der Fixes?
- Zusätzliche Akzeptanzkriterien?
- Andere technische Lösung für eines der Issues?

Lass es mich wissen!
