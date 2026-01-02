# Zusammenfassung ADR-039 bis ADR-042

## Ueberblick

Diese vier ADRs bilden zusammen einen **Quality & Reliability Sprint** fuer HELIX v4. Sie adressieren technische Schulden, Sicherheitsprobleme und UX-Bugs die im produktiven Betrieb aufgefallen sind.

---

## ADR-039: Code Quality Hardening - Paths, LSP, Documentation

**Status**: Proposed | **Scope**: major | **Type**: FIX/PROCESS

### Problem

Ein kritischer Code-Review hat systematische Probleme aufgedeckt:

1. **Hardcoded Paths** in 12 Dateien (z.B. `/home/aiuser01/helix-v4`)
   - Keine Portabilitaet zu Docker/CI
   - Tests funktionieren nicht auf anderen Maschinen

2. **LSP nicht aktiviert** - ADR-018 existiert seit 24.12.2024, wurde aber nie implementiert
   - `ENABLE_LSP_TOOL=1` nirgends gesetzt
   - Entwickler haben kein Go-to-Definition, keine References

3. **Dokumentations-Gaps** - Mehrere ADRs mit Status "Proposed" die "Implemented" sein sollten

4. **sys.path Anti-Pattern** - Fragile Python-Path Manipulation

### Loesung

| Phase | Massnahme |
|-------|-----------|
| 1 | `PathConfig` erweitern, alle Module migrieren, sys.path entfernen |
| 2 | `ENABLE_LSP_TOOL=1` setzen, pyright installieren |
| 3 | Dokumentation konsolidieren (CONFIGURATION-GUIDE.md, PATHS.md) |
| 4 | Verification - Tests auf anderem Verzeichnis |

---

## ADR-040: Ralph Automation Pattern

**Status**: Proposed | **Scope**: major | **Type**: NEW PROCESS

### Problem

ADR-Implementierung war bisher manuell und fehleranfaellig:

- Controller vergessen `files.modify` Schritte
- Automatische Verify-Scripts pruefen nur was reingeschrieben wurde
- **Textuelle ADR-Anforderungen werden nicht geprueft**
- Ralph gibt Promise aus obwohl nicht alle Phasen fertig sind

**Beispiel-Fehler bei ADR-039:**
```
Ralph machte Phase 1 (Paths) --> Integration Test OK --> Promise ausgegeben
                                          |
                         Phase 2 (LSP) vergessen!
                         Phase 3 (Docs) vergessen!
```

### Loesung: Consultant als intelligentes Verify

Die **Kern-Innovation** ist der Einsatz des Consultant als Verifikations-Instanz:

```
┌─────────────────────────────────────────────────────────────────┐
│                verify-with-consultant.sh                         │
│                                                                  │
│  1. Automatische Checks (schnell, billig)                       │
│     └── Files existieren? Tests gruen? Syntax OK?               │
│                          │                                       │
│                          v                                       │
│  2. Spawne Consultant mit ADR-Inhalt                            │
│                          │                                       │
│                          v                                       │
│  3. Consultant:                                                  │
│     ├── Liest ADR (versteht TEXTUELLE Anforderungen)            │
│     ├── Fuehrt EIGENE Checks aus (pyright, grep, etc.)          │
│     └── Verdict: PASSED + Promise ODER FAILED + was fehlt       │
└─────────────────────────────────────────────────────────────────┘
```

**Warum Consultant besser als Script:**

| Automatisches Script | Consultant |
|---------------------|------------|
| Prueft nur was reingeschrieben | Liest ADR komplett |
| Versteht keinen Kontext | "Default soll 1 sein" → prueft tatsaechlichen Wert |
| Kann keine neuen Checks | Fuehrt pyright, grep etc. selbst aus |
| Vergisst textuelle Reqs | Versteht "dokumentiert in X" |

---

## ADR-041: Reliability Fixes - Race Condition & Shell Injection

**Status**: Proposed | **Scope**: minor | **Type**: FIX

### Bug 1: Race Condition in Session Management

**TOCTOU** (Time-of-Check-Time-of-Use) Problem bei parallelen Requests:

```python
# Aktueller Code:
if self.session_exists(session_id):      # CHECK
    state = self.get_state(session_id)   # USE
else:
    state = self.create_session(...)     # WRITE
```

Bei parallelen Requests mit gleicher `conversation_id`:
1. Request A prueft: Session existiert nicht
2. Request B prueft: Session existiert nicht
3. Request A erstellt Session
4. **Request B ueberschreibt A's State!**

**Impact**: Datenverlust bei parallelen Requests in Open WebUI.

**Fix**: File-Locking mit `filelock` Library fuer atomare Session-Erstellung.

### Bug 2: Shell Injection in ConsultantVerifier

```python
result = subprocess.run(
    [str(self.spawn_script), prompt],  # prompt = ADR-Inhalt!
    ...
)
```

Bei speziell konstruiertem ADR-Inhalt koennte Shell-Code injiziert werden.

**Fix**: Prompt via stdin statt Argument uebergeben.

---

## ADR-042: Streaming Timeout Fix

**Status**: Implemented | **Scope**: hotfix | **Type**: FIX

### Problem

User-Report: Consultant-Chat "schmiert ab" - Antwort kommt nicht an.

**Root Cause:**

1. `_run_consultant_streaming()` sendet NUR `"[Starte Claude Code...]\n\n"` initial
2. Dann wartet es 3+ Minuten auf Claude Code
3. **KEIN Output waehrend dieser Zeit**
4. Open WebUI/Conduit hat Timeout (60-120s)
5. Verbindung wird geschlossen
6. Vollstaendige Antwort geht ins Leere

**Beweis aus Session**: 7896 bytes vollstaendige Antwort generiert - User hat sie nie erhalten!

### Fix: Queue-basiertes Live Streaming

```python
# Event Queue fuer Tool Calls
event_queue: Queue[str | None] = Queue()

# Heartbeat Task - alle 25s "." senden
async def heartbeat_task():
    while True:
        await asyncio.sleep(25)
        await event_queue.put(".")

# Tool Call Streaming
async def on_output(stream: str, line: str) -> None:
    # Parse JSONL und queue Tool Calls
    if data.get("type") == "tool_use":
        await event_queue.put(f"\n[{block.get('name')}] ")
```

**Ergebnis:**
- Kein Timeout mehr (Heartbeat haelt Verbindung aktiv)
- Besseres UX (User sieht `[Read]`, `[Write]`, `[Bash]` live)
- Debugging einfacher (Tool Calls sichtbar)

---

## Zusammenhaenge

```
ADR-039 (Quality)
    │
    ├── Definiert PathConfig, LSP Setup
    │
    └── Liefert Learnings fuer...
            │
            v
        ADR-040 (Ralph Pattern)
            │
            ├── Nutzt Consultant-Verify
            │
            └── ConsultantVerifier hat...
                    │
                    v
                ADR-041 (Security Fix)
                    │
                    └── Shell Injection Bug

ADR-042 (Streaming)
    │
    └── Unabhaengig - UX Bug aus Produktion
```

---

## Status-Uebersicht

| ADR | Status | Dringlichkeit |
|-----|--------|---------------|
| 039 | Proposed | Hoch (Portabilitaet) |
| 040 | Proposed | Mittel (Process) |
| 041 | Proposed | **Kritisch** (Security) |
| 042 | **Implemented** | War Hotfix |

<!-- STEP: done -->
