# HELIX Workflow System Implementation

> **Du bist der Orchestrator.** Du führst alle Phasen selbst aus, eine nach der anderen.

---

## 🎯 Deine Aufgabe

Implementiere das HELIX Workflow System (ADR-023 bis ADR-026).

**Phasen:**
1. LSP aktivieren (ADR-018) - ✅ DONE (Pyright installiert)
2. Workflow-Definitionen (ADR-023)
3. Consultant Workflow-Wissen (ADR-024)
4. Sub-Agent Verifikation (ADR-025)
5. Dynamische Phasen (ADR-026)
6. E2E Test

---

## 📋 Arbeitsweise

Für jede Phase:

1. **Lies die Phase-Instruktionen** in `phases/{N}/CLAUDE.md`
2. **Führe die Arbeit aus**
3. **Schreibe Output** nach `phases/{N}/output/`
4. **Verifiziere** dass alles funktioniert
5. **Gehe zur nächsten Phase**

Du kannst Sub-Sessions starten wenn nötig:
```bash
# Für isolierte Arbeit
claude --print -p "Aufgabe hier..."

# Oder via API
curl -X POST http://localhost:8001/helix/execute -d '{"project_path": "..."}'
```

---

## 🔧 Verfügbare Tools

- **LSP**: `ENABLE_LSP_TOOL=1` ist aktiv, Pyright installiert
- **API**: `http://localhost:8001/` (HELIX API)
- **Skills**: `skills/helix/`, `skills/helix/evolution/`, `skills/helix/adr/`

---

## 📁 Projekt-Struktur

```
projects/implement-workflow-system/
├── CLAUDE.md           # Diese Datei (Orchestrator-Instruktionen)
├── phases.yaml         # Phase-Definitionen
├── phases/
│   ├── 1/              # LSP (✅ DONE)
│   │   ├── CLAUDE.md
│   │   └── output/
│   ├── 2/              # Workflow-Definitionen
│   ├── 3/              # Consultant Wissen
│   ├── 4/              # Sub-Agent Verifikation
│   ├── 5/              # Dynamische Phasen
│   └── 6/              # E2E Test
```

---

## ✅ Akzeptanzkriterien (Gesamt)

- [ ] LSP funktioniert (Pyright, ENABLE_LSP_TOOL=1)
- [ ] 4 Workflow-Templates existieren (intern/extern × simple/complex)
- [ ] Consultant Template kennt Workflows
- [ ] Sub-Agent Verifikation mit 3x Retry implementiert
- [ ] Dynamische Phasen-Generierung (max 5, konfigurierbar)
- [ ] E2E Test: Consultant startet Workflow erfolgreich

---

## 🚀 START

Phase 1 ist bereits abgeschlossen. **Beginne mit Phase 2.**

Lies zuerst: `phases/2/CLAUDE.md`
