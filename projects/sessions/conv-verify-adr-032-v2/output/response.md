# ADR-032 Review: MCP Server für Hardware-Teststand-Orchestrierung

## Gesamtbewertung: **Gut strukturiert, einige Verbesserungen empfohlen**

Das ADR ist **grundsätzlich vollständig** und folgt dem HELIX ADR-Template. Die Architektur ist sinnvoll. Im Folgenden eine detaillierte Analyse:

---

## 1. Formale Vollständigkeit

### YAML Header: **Vollständig**

| Feld | Status | Wert |
|------|--------|------|
| `adr_id` | OK | "032" |
| `title` | OK | "MCP Server für Hardware-Teststand-Orchestrierung" |
| `status` | OK | "Proposed" |
| `project_type` | OK | "external" |
| `component_type` | OK | "SERVICE" |
| `classification` | OK | "NEW" |
| `change_scope` | OK | "major" |
| `files.create` | OK | 5 Dateien |
| `files.modify` | OK | [] (keine) |
| `files.docs` | OK | 1 Datei |
| `depends_on` | OK | [] |

### Pflicht-Sections: **Vollständig**

- [x] `## Kontext` - Vorhanden und gut erklärt
- [x] `## Entscheidung` - Vorhanden mit Architektur-Diagramm
- [x] `## Implementation` - Vorhanden mit Code-Beispielen
- [x] `## Dokumentation` - Vorhanden
- [x] `## Akzeptanzkriterien` - Vorhanden (13 Kriterien)
- [x] `## Konsequenzen` - Vorhanden mit Vorteilen/Nachteilen/Mitigation

---

## 2. Architektur-Bewertung

### Positiv

1. **Station-Konzept ist clever**
   - Abstrahiert Hardware zu logischen Einheiten
   - Erweiterbar für Scope/Motor ohne API-Änderung
   - Klare Ownership ("Agent arbeitet auf Station X")

2. **Recovery-Strategie gut durchdacht**
   - Automatischer Power-Cycle bei `0xFFFFFFFF` Error
   - Bekanntes NXP LPC55S69 Problem adressiert

3. **MCP-SDK korrekt verwendet**
   - `@app.tool()` Decorator Pattern
   - `stdio_server()` für Claude Desktop Integration
   - Async/await durchgängig

### Verbesserungsvorschläge

#### A. Fehlendes Error-Handling in Tools

Aktuell fehlt Exception-Handling für Netzwerk-Fehler:

```python
# Aktuell - kann bei Connection-Error crashen:
async with httpx.AsyncClient(timeout=30) as client:
    r = await client.post(...)

# Besser:
try:
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(...)
except httpx.TimeoutException:
    return f"Timeout connecting to {station}"
except httpx.ConnectError:
    return f"Cannot reach station {station} - check VPN"
```

**Empfehlung:** Akzeptanzkriterium hinzufügen:
`- [ ] Tools geben verständliche Fehlermeldungen bei Netzwerk-Problemen`

#### B. Fehlende Station-Locking

Wenn zwei Claude-Sessions gleichzeitig auf dieselbe Station zugreifen:

```
Claude A: station_flash("dev-1", "fw1.bin")
Claude B: station_reset("dev-1")  # Mitten im Flash!
```

**Empfehlung:** Einfaches Lock-Mechanismus hinzufügen (Phase 1 oder 2):

```python
# In-Memory Lock (für Single-Instance MCP Server)
station_locks: dict[str, str] = {}  # station -> session_id

@app.tool()
async def station_acquire(station: str) -> str:
    """Acquire exclusive access to a station."""
    ...

@app.tool()
async def station_release(station: str) -> str:
    """Release exclusive access to a station."""
    ...
```

#### C. Fehlende Logging/Audit

Für Hardware-Debugging ist es kritisch zu wissen WER WANN WAS gemacht hat.

**Empfehlung:** Akzeptanzkriterium hinzufügen:
`- [ ] Alle Tool-Aufrufe werden mit Timestamp geloggt`

#### D. Config-Reload

Die Config wird bei jedem Tool-Call neu geladen (`load_config()`). Das ist für 2 Stationen OK, aber bei 20 Stationen ineffizient.

**Empfehlung:** Config caching mit reload-on-signal:

```python
_config_cache: dict | None = None

def load_config(force_reload: bool = False) -> dict:
    global _config_cache
    if _config_cache is None or force_reload:
        with open("config.yaml") as f:
            _config_cache = yaml.safe_load(f)
    return _config_cache
```

---

## 3. Fehlende Elemente

### A. Keine Tests definiert

Das ADR hat keine Test-Strategie. Für Hardware-Interaktion ist das kritisch.

**Empfehlung:** Section `## Tests` hinzufügen:

```markdown
## Tests

### Unit Tests (mit Mock)
- Test config loading
- Test station lookup (valid/invalid)
- Test error message formatting

### Integration Tests (gegen echte Hardware)
- Test connect/health/recover flow
- Test flash cycle
- Test concurrent access handling

### Mocking Strategie
```python
# Für Unit Tests ohne Hardware:
@pytest.fixture
def mock_fpga():
    with respx.mock:
        respx.get("http://192.168.178.19:8080/health").respond(
            json={"status": "ok", "jlink": {"connected": True}}
        )
        yield
```

### B. Keine Security-Überlegungen

Der MCP Server hat Zugriff auf kritische Hardware (Flash, Power).

**Empfehlung:** Section `## Sicherheit` hinzufügen:

```markdown
## Sicherheit

### Risiken
- Unauthorized station access (z.B. falsche Firmware flashen)
- DoS durch Power-Cycle Loops

### Mitigations
- MCP Server nur auf localhost binden (Claude Desktop verbindet lokal)
- Rate-limiting für power-cycle (max 1x/10s pro Station)
- Audit-Log aller destructive operations (flash, power, reset)
```

### C. Deployment nicht beschrieben

Wie wird der MCP Server installiert und gestartet?

**Empfehlung:** In README.md oder ADR:

```markdown
## Deployment

### Installation
```bash
cd /home/aiuser01/mcp-hardware
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Claude Desktop Config
```json
{
  "mcpServers": {
    "hardware-teststand": {
      "command": "/home/aiuser01/mcp-hardware/.venv/bin/python",
      "args": ["server.py"],
      "cwd": "/home/aiuser01/mcp-hardware"
    }
  }
}
```

### Systemd Service (optional)
Für dauerhaften Betrieb als Service.
```

---

## 4. Akzeptanzkriterien-Check

Aktuelle Kriterien sind **sinnvoll aber unvollständig**:

| Vorhanden | Fehlt |
|-----------|-------|
| Funktionale Tools (9 Kriterien) | Error-Handling |
| MCP Server Start | Unit Tests |
| Claude Desktop Integration | Integration Tests |
| Recovery-Flow | Logging/Audit |
| README.md | Security Review |
| Config-Beispiel | Deployment-Anleitung |

**Empfehlung:** Diese Kriterien hinzufügen:

```markdown
### Error Handling
- [ ] Netzwerk-Timeouts geben verständliche Meldungen
- [ ] Ungültige Station-Namen werden abgefangen
- [ ] FPGA-API-Fehler werden sauber propagiert

### Tests
- [ ] Unit Tests für config loading und station lookup
- [ ] Mock-basierte Tests für Tool-Responses

### Operations
- [ ] Tool-Aufrufe werden geloggt (station, action, timestamp)
- [ ] Deployment-Anleitung in README.md
```

---

## 5. Kleinere Hinweise

### Code-Stil

1. **Type Hints fehlen** in Funktionen:
   ```python
   # Aktuell:
   def get_station(name: str) -> dict:

   # Besser (mit TypedDict oder dataclass):
   def get_station(name: str) -> StationConfig:
   ```

2. **Magic Numbers**:
   ```python
   length = min(length, 256)  # Warum 256?
   hex_str = " ".join(... for b in mem[:64])  # Warum 64?
   ```
   Sollten als Konstanten mit Kommentar definiert werden.

### Dateistruktur

Header sagt `mcp-hardware/stations.py` wird erstellt, aber im Code ist alles in `server.py`. Entweder:
- `stations.py` aus `files.create` entfernen, oder
- Station-Logic in `stations.py` auslagern

---

## 6. Zusammenfassung

### Stärken
- Saubere ADR-Struktur nach HELIX-Template
- Station-Konzept ist architektonisch sinnvoll
- Gute Code-Beispiele mit async/await
- Recovery-Strategie für bekannte Hardware-Probleme

### Verbesserungen empfohlen
1. **Error-Handling** für Netzwerk-Fehler in Tools
2. **Tests-Section** mit Unit/Integration-Strategie
3. **Security-Section** für Hardware-Zugriff
4. **Deployment-Anleitung** in README oder ADR
5. **Logging** für Audit-Trail
6. **Konsistenz**: `stations.py` in Header vs. Code

### Bewertung

| Aspekt | Note |
|--------|------|
| Formale Vollständigkeit | **A** |
| Architektur | **B+** |
| Implementation Details | **B** |
| Akzeptanzkriterien | **B-** |
| Produktionsreife | **C+** (fehlt Error-Handling, Tests, Security) |

---

## Nächste Schritte

1. Entscheide ob die Verbesserungen in Phase 1 oder später kommen sollen
2. Ergänze die fehlenden Sections (Tests, Security, Deployment)
3. Korrigiere die `files.create` Liste (stations.py?)
4. Füge Error-Handling-Kriterien hinzu

Soll ich ein überarbeitetes ADR mit den Verbesserungen erstellen?
