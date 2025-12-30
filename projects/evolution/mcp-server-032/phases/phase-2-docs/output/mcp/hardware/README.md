# HELIX Hardware MCP Server

> MCP Server for Hardware Test Station Orchestration via FPGA + J-Link
>
> ADR-032 | FastMCP 2.0

---

## Overview

The HELIX Hardware MCP Server enables AI assistants (Claude, ChatGPT) to control physical hardware test stations. It provides exclusive access management, debug operations, and audit logging for embedded development workflows.

### Features

- **Multi-Client Support**: Works with Claude Desktop (stdio/SSE) and ChatGPT (Streamable HTTP)
- **Station Locking**: Exclusive access prevents conflicts
- **Debug Operations**: Connect, halt, step, memory read/write, flash
- **Recovery Tools**: Power-cycle locked targets
- **Audit Logging**: Track all operations for compliance

---

## Quick Start

### Installation

```bash
# Clone and install
cd mcp/hardware
pip install -r ../base/requirements.txt
pip install httpx pyyaml
```

### Running the Server

```bash
# For Claude Desktop (local)
python server.py stdio

# For Claude Desktop (remote via SSE)
python server.py sse

# For ChatGPT (Streamable HTTP)
python server.py http
```

### Claude Desktop Configuration

Add to `~/.config/claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "helix-hardware": {
      "command": "python",
      "args": ["/path/to/mcp/hardware/server.py", "stdio"]
    }
  }
}
```

---

## Available Tools

### Locking Tools

| Tool | Description |
|------|-------------|
| `station_acquire` | Acquire exclusive access to a station |
| `station_release` | Release exclusive access |

### Station Tools

| Tool | Description |
|------|-------------|
| `list_stations` | List all available stations with status |
| `station_connect` | Connect to station's debug target |
| `station_recover` | Power-cycle and reconnect |

### Debug Tools

| Tool | Description |
|------|-------------|
| `station_registers` | Read CPU registers |
| `station_halt` | Halt CPU execution |
| `station_go` | Resume CPU execution |
| `station_reset` | Reset target MCU |
| `station_memory_read` | Read memory from target |
| `station_flash` | Flash firmware to target |

### Monitoring Tools

| Tool | Description |
|------|-------------|
| `station_audit_history` | View recent operations on a station |

---

## Usage Examples

### Basic Workflow

```
User: List available test stations

AI: [Calls list_stations]
    Available stations:
      station-alpha: Test Station Alpha - Nordic nRF5340 [available]
      station-beta: Test Station Beta - STM32L5 [available]
      station-gamma: Test Station Gamma - ESP32-S3 [LOCKED by session-xyz]

User: Acquire station-alpha for my session

AI: [Calls station_acquire(station="station-alpha", session_id="my-session")]
    Lock acquired on station-alpha for 300s

User: Connect to station-alpha

AI: [Calls station_connect(station="station-alpha")]
    Connected to station-alpha

User: Read the CPU registers

AI: [Calls station_registers(station="station-alpha")]
    Registers on station-alpha:
      PC: 0x08000100
      SP: 0x20008000
      LR: 0x08000105
      R0: 0x00000000
      R1: 0x00000001

User: Release the station

AI: [Calls station_release(station="station-alpha", session_id="my-session")]
    Lock released on station-alpha
```

### Recovery from Locked Target

```
User: Connect to station-beta

AI: [Calls station_connect(station="station-beta")]
    Target locked. Use station_recover to power-cycle.

User: Recover station-beta

AI: [Calls station_recover(station="station-beta")]
    Recovery successful! station-beta reconnected.
```

### Flashing Firmware

```
User: Flash the new firmware to station-alpha

AI: [Calls station_flash(station="station-alpha", firmware_path="/path/to/app.hex")]
    Firmware flashed to station-alpha (1234ms)
```

---

## Configuration

### Station Configuration (config.yaml)

```yaml
stations:
  station-alpha:
    description: "Test Station Alpha - Nordic nRF5340"
    fpga:
      host: "192.168.1.101"
      port: 5000
      voltage: 3.3
    jlink:
      serial: "123456789"
      device: "nRF5340_xxAA"
      interface: "SWD"
      speed: 4000
```

### Lock Settings

```yaml
locking:
  default_timeout: 300  # 5 minutes
  max_timeout: 3600     # 1 hour
```

### Audit Settings

```yaml
audit:
  enabled: true
  log_dir: "./logs/audit"
  retention_days: 30
```

---

## Architecture

### Server Structure

```
mcp/hardware/
├── server.py        # Main MCP server with tools
├── locking.py       # Station lock manager
├── audit.py         # Audit logging
├── config.yaml      # Station configuration
└── docs/
    └── JLINK_API.md # J-Link API reference
```

### Components

| Component | Description |
|-----------|-------------|
| `server.py` | FastMCP server exposing all MCP tools |
| `locking.py` | Thread-safe station locking with timeout |
| `audit.py` | Structured audit logging to JSONL files |
| `config.yaml` | Station definitions and settings |

---

## Transport Options

| Transport | Command | Use Case |
|-----------|---------|----------|
| stdio | `python server.py stdio` | Claude Desktop local |
| SSE | `python server.py sse` | Claude Desktop remote |
| HTTP | `python server.py http` | ChatGPT / Web clients |

### SSE/HTTP Server Settings

Default: `0.0.0.0:8000`

For HTTP transport, the MCP endpoint is at `/mcp`.

---

## Audit Logging

All station operations are logged to:

- `logs/audit/audit.log` - Rolling log file
- `logs/audit/audit-YYYY-MM-DD.jsonl` - Daily JSONL files

### Log Entry Format

```json
{
  "timestamp": "2024-01-15T10:30:00.000Z",
  "station": "station-alpha",
  "operation": "connect",
  "session_id": "my-session",
  "result": "success",
  "duration_ms": 234
}
```

---

## Error Handling

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `Unknown station: {name}` | Station not in config | Check config.yaml |
| `Station locked by {session}` | Another session holds lock | Wait or contact owner |
| `Timeout connecting` | Network issue | Check VPN/network |
| `Target locked (0xFFFFFFFF)` | MCU in debug lock | Use station_recover |
| `Cannot reach station` | FPGA offline | Power cycle FPGA |

---

## Development

### Testing with MCP Inspector

```bash
npx @modelcontextprotocol/inspector python server.py stdio
```

### Adding New Tools

1. Add tool function with `@mcp.tool` decorator
2. Add docstring with parameter descriptions
3. Handle errors gracefully
4. Log operations via `audit.log()`

---

## References

- [ADR-032: MCP Server for Hardware Test Stations](../../ADR-032.md)
- [J-Link API Reference](docs/JLINK_API.md)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [MCP Specification](https://modelcontextprotocol.io/)