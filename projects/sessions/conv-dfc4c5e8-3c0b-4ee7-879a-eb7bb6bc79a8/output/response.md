# ADR-039: Code Quality Hardening

## Zusammenfassung

Basierend auf der kritischen Code-Review wurde **ADR-039** erstellt, das drei Hauptprobleme adressiert:

### 1. Hardcoded Paths (12 Dateien)
- Test-System funktioniert aktuell NICHT auf anderen Maschinen
- `PathConfig` existiert bereits (ADR-035), wird aber inkonsistent genutzt
- `sys.path.insert()` Anti-Pattern in 2 Dateien

### 2. LSP nicht aktiviert
- ADR-018 existiert seit 24.12.2024 aber wurde nie implementiert
- `ENABLE_LSP_TOOL=1` wird nirgends gesetzt
- Entwickler haben keine Go-to-Definition, Find-References, etc.

### 3. Dokumentations-Gaps
- ADR-019, ADR-020: "Proposed" aber nie implementiert
- ADR-020 hat widersprüchlichen Status-Marker!
- ConsultantMeeting für Multi-Expert-Szenarien nicht dokumentiert

---

## Was wurde erstellt

| Datei | Beschreibung |
|-------|--------------|
| `adr/039-code-quality-hardening---paths-lsp-documentation.md` | Finalisiertes ADR |
| `output/phases.yaml` | 4-Phasen Implementation Plan |
| `adr/INDEX.md` | Aktualisiert mit ADR-039 |

---

## 4 Phasen

1. **Path Consolidation** - PathConfig erweitern, 12 Dateien migrieren
2. **LSP Activation** - env.sh, pyproject.toml, ADR-018 Status
3. **Documentation** - CONFIGURATION-GUIDE.md, PATHS.md, ConsultantMeeting Doku
4. **Verification** - Tests, Grep-Checks, LSP verifizieren

---

## Akzeptanzkriterien (Auszug)

- [ ] Keine hardcoded "/home/aiuser01" Pfade mehr
- [ ] Kein `sys.path.insert()` mehr
- [ ] `ENABLE_LSP_TOOL=1` in config/env.sh
- [ ] pyright in pyproject.toml
- [ ] ConsultantMeeting dokumentiert
- [ ] ADR-018, ADR-020 Status korrigiert

---

## Nächste Schritte

1. ADR-039 reviewen
2. Bei Zustimmung: Status auf "Accepted" setzen
3. Evolution starten mit `phases.yaml`

---

**Pfad zum ADR:** `adr/039-code-quality-hardening---paths-lsp-documentation.md`
