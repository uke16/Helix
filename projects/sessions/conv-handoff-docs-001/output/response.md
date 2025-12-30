# Dokumentations-Checkliste: Handoff für Implementierung

Basierend auf der heutigen Arbeit und den HELIX-Dokumentationsrichtlinien hier die vollständige Checkliste.

---

## 1. ADRs (Architecture Decision Records)

Nach HELIX-Konvention gehören alle ADRs nach `/adr/NNN-name.md`.

| ADR | Datei | Status | Aktion |
|-----|-------|--------|--------|
| ADR-032 | `adr/032-mcp-server-hardware.md` | Draft? | Finalisieren + INDEX.md aktualisieren |
| ADR-033 | `adr/033-consultant-legacy-cleanup.md` | Draft? | Finalisieren + INDEX.md aktualisieren |
| DRAFT Services Layer | - | Nur Konzept | Bei Bedarf als ADR-034 formalisieren |

### ADR-Checkliste pro ADR:

- [ ] YAML Frontmatter vollständig (`adr_id`, `title`, `status`, `files`)
- [ ] Sections: `## Kontext`, `## Entscheidung`, `## Implementation`, `## Dokumentation`, `## Akzeptanzkriterien`, `## Konsequenzen`
- [ ] Mindestens 3 Akzeptanzkriterien als Checkboxen
- [ ] `files.create` / `files.modify` / `files.docs` korrekt befüllt
- [ ] ADR nach `adr/` verschoben (via `finalize_adr()`)
- [ ] `adr/INDEX.md` aktualisiert mit neuem Eintrag

**Validierung:**
```bash
python -m helix.tools.adr_tool validate adr/032-mcp-server-hardware.md
python -m helix.tools.adr_tool finalize adr/032-mcp-server-hardware.md
```

---

## 2. MCP Server Struktur

Nach der heutigen Diskussion:

```
mcp/
├── base/                      # Basis-Implementierung
│   ├── __init__.py
│   ├── server.py             # FastMCP Server
│   └── README.md             # Dokumentation
│
└── hardware/                  # Hardware-spezifisch
    ├── __init__.py
    ├── tools/
    │   ├── locking.py        # Hardware-Locking
    │   ├── audit.py          # Audit-Trail
    │   └── jlink.py          # J-Link API
    └── README.md             # Hardware MCP Dokumentation
```

### MCP-Checkliste:

- [ ] `mcp/base/README.md` - Wie man einen MCP Server erstellt
- [ ] `mcp/hardware/README.md` - Hardware-spezifische Tools
- [ ] Docstrings für alle Tools (werden automatisch als Tool-Descriptions verwendet)
- [ ] `pyproject.toml` oder `requirements.txt` für Abhängigkeiten (fastmcp, etc.)

---

## 3. Skills

Skills gehören nach `/skills/{domain}/SKILL.md`.

| Skill | Datei | Status |
|-------|-------|--------|
| Hardware | `skills/hardware/SKILL.md` | Erstellen |

### Skill-Checkliste:

- [ ] `skills/hardware/SKILL.md` erstellt
- [ ] Enthält: Domain-Wissen, API-Referenzen, Beispiele
- [ ] In `docs/ARCHITECTURE-MODULES.md` referenziert (falls neues Modul)

---

## 4. Architektur-Dokumentation

| Dokument | Was muss rein | Priorität |
|----------|--------------|-----------|
| `docs/ARCHITECTURE-MODULES.md` | MCP Server Modul-Beschreibung | Hoch |
| `docs/ARCHITECTURE-MODULES.md` | Hardware Tools Section | Hoch |
| `adr/INDEX.md` | ADR-032, ADR-033 Einträge | Hoch |
| `ONBOARDING.md` | (nur wenn grundlegende Konzepte ändern) | Niedrig |

---

## 5. Code-Dokumentation (Docstrings)

Jede Public API braucht:

```python
def lock_hardware(device_id: str, user: str) -> LockResult:
    """Sperrt ein Hardware-Gerät für exklusiven Zugriff.

    Implementiert gemäß ADR-032.

    Args:
        device_id: Eindeutige Geräte-ID
        user: Benutzername für Audit-Trail

    Returns:
        LockResult mit lock_id und expires_at

    Raises:
        DeviceLockedException: Wenn Gerät bereits gesperrt
    """
```

### Docstring-Checkliste:

- [ ] Alle MCP Tools haben Docstrings (FastMCP nutzt diese!)
- [ ] ADR-Referenz in relevanten Docstrings
- [ ] Type Hints für alle Parameter und Return-Werte

---

## 6. Zusammenfassung: Was wo?

| Artifact | Ort | Format |
|----------|-----|--------|
| Architektur-Entscheidungen | `adr/NNN-name.md` | ADR Template v2 |
| Modul-Dokumentation | `docs/ARCHITECTURE-MODULES.md` | Markdown + Code |
| Domain-Wissen | `skills/{domain}/SKILL.md` | Skill-Format |
| Code-Dokumentation | Im Code selbst | Docstrings |
| MCP Server Docs | `mcp/{name}/README.md` | Markdown |
| ADR-Index | `adr/INDEX.md` | Tabellen |

---

## 7. Prioritäten für nächste Session

### Must Have (vor Implementierung):
1. ADR-032 finalisieren und validieren
2. ADR-033 finalisieren und validieren
3. `adr/INDEX.md` aktualisieren

### Should Have (während Implementierung):
4. `mcp/base/` Struktur anlegen
5. `mcp/hardware/` Struktur anlegen
6. `skills/hardware/SKILL.md` erstellen

### Nice to Have (nach Implementierung):
7. `docs/ARCHITECTURE-MODULES.md` um MCP-Section erweitern
8. HELIX Services Layer als ADR-034 formalisieren (wenn Scope klar)

---

## Fragen zur Klärung

Bevor wir weitermachen:

1. **Wo liegen die ADR-Drafts aktuell?**
   - In `adr/` (noch ohne INDEX-Eintrag)?
   - In einem Session-Verzeichnis?
   - Nur als Konzept im Kopf?

2. **HELIX Services Layer**:
   - Soll das ein eigenständiges ADR werden?
   - Oder ist es Teil von ADR-032?

3. **MCP Server**:
   - Gibt es schon Code in `mcp/` oder nur die Konzept-Diskussion?

---

*Diese Checkliste basiert auf den HELIX-Richtlinien aus:*
- `skills/helix/adr/SKILL.md`
- `docs/ARCHITECTURE-MODULES.md`
- `adr/INDEX.md`
