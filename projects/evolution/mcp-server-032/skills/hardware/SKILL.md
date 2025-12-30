# Hardware Test Station Skill

> Domain knowledge for controlling hardware test stations via MCP
>
> ADR-032: MCP Server for Hardware Test Station Orchestration

---

## Overview

This skill provides knowledge for AI assistants to effectively control hardware test stations (FPGA + J-Link debuggers) through the HELIX Hardware MCP Server.

### When to Read This Skill

- Working with embedded development workflows
- Debugging or testing embedded firmware
- Flashing firmware to development boards
- Recovering locked or unresponsive targets

---

## Key Concepts

### Test Stations

A test station is a physical setup containing:

- **FPGA Controller**: Provides HTTP API for J-Link operations
- **J-Link Debugger**: SEGGER debug probe connected to target
- **Target MCU**: The microcontroller being tested (nRF5340, STM32, ESP32, etc.)

### Station Locking

Stations require **exclusive access** to prevent conflicts:

1. **Acquire** lock before any operations
2. Lock has a **timeout** (default 5 minutes)
3. **Release** lock when done
4. Expired locks are automatically cleaned up

### Debug Operations

Core debug operations:

| Operation | Description | Prerequisite |
|-----------|-------------|--------------|
| Connect | Establish debug connection | Lock acquired |
| Halt | Stop CPU execution | Connected |
| Go | Resume execution | Connected, halted |
| Reset | Reset target MCU | Connected |
| Registers | Read CPU registers | Connected, halted |
| Memory Read | Read target memory | Connected, halted |
| Flash | Program firmware | Connected |
| Recover | Power-cycle target | Lock acquired |

---

## Workflow Patterns

### Standard Debug Session

```
1. list_stations          → See available stations
2. station_acquire        → Get exclusive access
3. station_connect        → Establish debug connection
4. [debug operations]     → halt, registers, memory_read, etc.
5. station_release        → Release lock
```

### Firmware Update

```
1. station_acquire        → Get exclusive access
2. station_connect        → Establish connection
3. station_halt           → Stop execution (optional)
4. station_flash          → Program new firmware
5. station_reset          → Reset to run new code
6. station_release        → Release lock
```

### Recovery from Error State

```
1. station_acquire        → Get exclusive access
2. station_connect        → Attempt connection
   → If "Target locked (0xFFFFFFFF)":
3. station_recover        → Power-cycle and reconnect
4. [continue with operations]
5. station_release        → Release lock
```

---

## Common Scenarios

### Scenario: Target Not Responding

**Symptoms:**
- Connection timeout
- `0xFFFFFFFF` read from registers

**Solution:**
```
1. Use station_recover to power-cycle
2. If still failing, check physical connections
3. May need to manually reset FPGA controller
```

### Scenario: Station Already Locked

**Symptoms:**
- `Station locked by {session_id}` error

**Solution:**
```
1. Check who holds the lock (audit history)
2. Wait for timeout (default 5 min)
3. Or coordinate with lock holder
```

### Scenario: Network Unreachable

**Symptoms:**
- `Cannot reach station` error
- Connection refused

**Solution:**
```
1. Check VPN connection
2. Verify FPGA controller is powered on
3. Check station configuration in config.yaml
```

---

## Tool Reference

### station_acquire

Acquire exclusive access to a station.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| station | str | Yes | Station name (e.g., "station-alpha") |
| session_id | str | Yes | Unique session identifier |
| timeout | int | No | Lock timeout in seconds (default: 300) |

**Returns:** Success message or lock conflict information

**Example:**
```
station_acquire(station="station-alpha", session_id="debug-001", timeout=600)
→ "Lock acquired on station-alpha for 600s"
```

---

### station_release

Release exclusive access to a station.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| station | str | Yes | Station name |
| session_id | str | Yes | Session that holds the lock |

**Returns:** Success or failure message

**Example:**
```
station_release(station="station-alpha", session_id="debug-001")
→ "Lock released on station-alpha"
```

---

### list_stations

List all available hardware test stations with their status.

**Parameters:** None

**Returns:** Formatted list of stations with descriptions and lock status

**Example:**
```
list_stations()
→ Available stations:
    station-alpha: Test Station Alpha - Nordic nRF5340 [available]
    station-beta: Test Station Beta - STM32L5 [LOCKED by session-xyz]
```

---

### station_connect

Connect to a station's debug target via J-Link.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| station | str | Yes | Station name |

**Returns:** Connection status message

**Example:**
```
station_connect(station="station-alpha")
→ "Connected to station-alpha"
```

---

### station_recover

Recover a station from error state by power-cycling the target.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| station | str | Yes | Station name |

**Returns:** Recovery status message

**Example:**
```
station_recover(station="station-alpha")
→ "Recovery successful! station-alpha reconnected."
```

---

### station_registers

Read CPU registers from the station's target.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| station | str | Yes | Station name |

**Returns:** Formatted register values or error

**Example:**
```
station_registers(station="station-alpha")
→ Registers on station-alpha:
    PC: 0x08000100
    SP: 0x20008000
    LR: 0x08000105
    R0: 0x00000000
```

---

### station_halt

Halt the CPU on the station's target.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| station | str | Yes | Station name |

**Returns:** Halt status message

---

### station_go

Resume CPU execution on the station's target.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| station | str | Yes | Station name |

**Returns:** Resume status message

---

### station_reset

Reset the target MCU on a station.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| station | str | Yes | Station name |

**Returns:** Reset status message

---

### station_memory_read

Read memory from the station's target.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| station | str | Yes | Station name |
| address | str | Yes | Memory address (hex, e.g., "0x20000000") |
| length | int | No | Bytes to read (default: 64) |

**Returns:** Hex dump of memory or error

**Example:**
```
station_memory_read(station="station-alpha", address="0x20000000", length=32)
→ Memory at 0x20000000 (32 bytes):
    20000000: 00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F  ................
    20000010: 10 11 12 13 14 15 16 17 18 19 1A 1B 1C 1D 1E 1F  ................
```

---

### station_flash

Flash firmware to the station's target.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| station | str | Yes | Station name |
| firmware_path | str | Yes | Path to firmware file (.hex or .bin) |
| verify | bool | No | Verify after flashing (default: True) |

**Returns:** Flash status message

**Example:**
```
station_flash(station="station-alpha", firmware_path="/path/to/app.hex")
→ "Firmware flashed to station-alpha (1234ms)"
```

---

### station_audit_history

Get recent audit history for a station.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| station | str | Yes | Station name |
| limit | int | No | Max entries (default: 20) |

**Returns:** Formatted audit history

---

## Best Practices

### Always Acquire Before Operating

```
# Good
station_acquire(station="station-alpha", session_id="my-session")
station_connect(station="station-alpha")
...
station_release(station="station-alpha", session_id="my-session")

# Bad - may conflict with other users
station_connect(station="station-alpha")  # Without acquiring first
```

### Use Meaningful Session IDs

```
# Good - traceable
session_id="firmware-test-2024-01-15-user1"

# Bad - not traceable
session_id="test"
```

### Handle Errors Gracefully

```
# Check connection result before proceeding
result = station_connect(station="station-alpha")
if "Target locked" in result:
    station_recover(station="station-alpha")
```

### Release Locks When Done

Unreleased locks block others for 5+ minutes. Always release:

```
# Even if operations fail, release the lock
station_release(station="station-alpha", session_id="my-session")
```

---

## Troubleshooting

### Debug Connection Issues

1. **Verify station exists:** `list_stations`
2. **Check lock status:** Look for `[LOCKED by ...]` in listing
3. **Try recovery:** `station_recover` power-cycles the target
4. **Check audit history:** `station_audit_history` shows recent operations

### Firmware Flash Failures

1. **Verify file exists:** Check firmware_path is accessible
2. **Check target connected:** `station_connect` first
3. **Try with halt:** `station_halt` before flash
4. **Use recovery:** Power-cycle if target is stuck

---

## Related Documentation

- [Hardware Server README](../../mcp/hardware/README.md)
- [J-Link API Reference](../../mcp/hardware/docs/JLINK_API.md)
- [ADR-032](../../ADR-032.md)
