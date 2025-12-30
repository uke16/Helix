# J-Link API Reference

> API Reference for HELIX Hardware MCP Server J-Link Integration
>
> ADR-032: MCP Server for Hardware Test Station Orchestration

---

## Overview

The HELIX Hardware MCP Server communicates with FPGA controllers that expose J-Link debug probe functionality via HTTP REST APIs. This document describes the underlying API that the MCP tools use.

### Architecture

```
┌──────────────────────┐     MCP Protocol      ┌──────────────────────┐
│  Claude / ChatGPT    │◄────────────────────►│  MCP Hardware Server │
│  (AI Client)         │   stdio/SSE/HTTP      │  (helix-hardware)    │
└──────────────────────┘                       └──────────┬───────────┘
                                                          │ HTTP REST
                                                          ▼
                                               ┌──────────────────────┐
                                               │   FPGA Controller    │
                                               │   (J-Link Wrapper)   │
                                               └──────────┬───────────┘
                                                          │ USB/JTAG/SWD
                                                          ▼
                                               ┌──────────────────────┐
                                               │   Target MCU         │
                                               │   (nRF5340, STM32)   │
                                               └──────────────────────┘
```

---

## FPGA Controller Endpoints

The FPGA controller exposes the following HTTP endpoints for J-Link operations.

### Base URL

```
http://{fpga_host}:{fpga_port}
```

Default port: `5000`

---

### POST /jlink/connect

Establish connection to the debug target via J-Link.

**Request:**
```http
POST /jlink/connect HTTP/1.1
Host: 192.168.1.101:5000
```

**Response (Success):**
```json
{
  "success": true,
  "stdout": "SEGGER J-Link Commander V7.92\nConnecting to target...\nCortex-M33 identified.\nTarget connection established."
}
```

**Response (Target Locked):**
```json
{
  "success": false,
  "stdout": "Connecting to target...\nReading IDCODE: 0xFFFFFFFF\nTarget connection failed."
}
```

**MCP Tool:** `station_connect`

---

### POST /jlink/power

Control target power supply via J-Link.

**Request:**
```http
POST /jlink/power HTTP/1.1
Host: 192.168.1.101:5000
Content-Type: application/json

{
  "action": "cycle",
  "voltage": 3.3
}
```

**Parameters:**
| Name | Type | Description |
|------|------|-------------|
| `action` | string | `on`, `off`, or `cycle` |
| `voltage` | float | Target voltage (1.8, 2.5, or 3.3V) |

**Response:**
```json
{
  "success": true,
  "message": "Power cycled at 3.3V"
}
```

**MCP Tool:** `station_recover` (uses `cycle` action)

---

### GET /jlink/registers

Read CPU registers from the halted target.

**Request:**
```http
GET /jlink/registers HTTP/1.1
Host: 192.168.1.101:5000
```

**Response:**
```json
{
  "success": true,
  "registers": {
    "PC": 134217728,
    "SP": 536870912,
    "LR": 134217732,
    "R0": 0,
    "R1": 1,
    "R2": 2,
    "R3": 3,
    "R4": 0,
    "R5": 0,
    "R6": 0,
    "R7": 0
  }
}
```

**MCP Tool:** `station_registers`

---

### POST /jlink/halt

Halt CPU execution.

**Request:**
```http
POST /jlink/halt HTTP/1.1
Host: 192.168.1.101:5000
```

**Response:**
```json
{
  "success": true,
  "message": "CPU halted"
}
```

**MCP Tool:** `station_halt`

---

### POST /jlink/go

Resume CPU execution.

**Request:**
```http
POST /jlink/go HTTP/1.1
Host: 192.168.1.101:5000
```

**Response:**
```json
{
  "success": true,
  "message": "CPU running"
}
```

**MCP Tool:** `station_go`

---

### POST /jlink/reset

Reset the target MCU.

**Request:**
```http
POST /jlink/reset HTTP/1.1
Host: 192.168.1.101:5000
```

**Response:**
```json
{
  "success": true,
  "message": "Target reset"
}
```

**MCP Tool:** `station_reset`

---

### GET /jlink/memory

Read memory from target.

**Request:**
```http
GET /jlink/memory?address=536870912&length=64 HTTP/1.1
Host: 192.168.1.101:5000
```

**Parameters:**
| Name | Type | Description |
|------|------|-------------|
| `address` | int | Start address (decimal) |
| `length` | int | Number of bytes to read |

**Response:**
```json
{
  "success": true,
  "data": "0102030405060708090A0B0C0D0E0F10..."
}
```

The `data` field contains hex-encoded bytes.

**MCP Tool:** `station_memory_read`

---

### POST /jlink/flash

Flash firmware to target.

**Request:**
```http
POST /jlink/flash HTTP/1.1
Host: 192.168.1.101:5000
Content-Type: multipart/form-data; boundary=----FormBoundary

------FormBoundary
Content-Disposition: form-data; name="firmware"; filename="app.hex"
Content-Type: application/octet-stream

[Binary firmware data]
------FormBoundary
Content-Disposition: form-data; name="verify"

true
------FormBoundary--
```

**Parameters:**
| Name | Type | Description |
|------|------|-------------|
| `firmware` | file | Firmware file (.hex or .bin) |
| `verify` | string | `true` or `false` for verification |

**Response:**
```json
{
  "success": true,
  "message": "Flashed 32768 bytes, verified OK"
}
```

**MCP Tool:** `station_flash`

---

## Error Handling

### Common Error Responses

**Network Error:**
```json
{
  "success": false,
  "error": "Connection refused"
}
```

**Timeout:**
```json
{
  "success": false,
  "error": "Operation timed out"
}
```

**Target Not Connected:**
```json
{
  "success": false,
  "error": "No target connection"
}
```

### Recovery Procedures

1. **Target Locked (0xFFFFFFFF):**
   - Use `station_recover` to power-cycle
   - Retry connection

2. **Network Error:**
   - Check VPN connection
   - Verify FPGA controller is powered on
   - Check station configuration in config.yaml

3. **Timeout:**
   - Increase timeout in client
   - Check for target errata or debug access issues

---

## Station Configuration

Stations are configured in `config.yaml`:

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

### Configuration Fields

| Field | Description |
|-------|-------------|
| `fpga.host` | IP address of FPGA controller |
| `fpga.port` | HTTP port (default: 5000) |
| `fpga.voltage` | Target voltage for power operations |
| `jlink.serial` | J-Link serial number |
| `jlink.device` | Target device name |
| `jlink.interface` | Debug interface (SWD/JTAG) |
| `jlink.speed` | Debug clock speed in kHz |

---

## Supported Targets

| Device | Interface | Notes |
|--------|-----------|-------|
| Nordic nRF5340 | SWD | Dual-core Cortex-M33 |
| STM32L5xx | SWD | TrustZone support |
| ESP32-S3 | JTAG | Dual-core Xtensa LX7 |

---

## References

- [SEGGER J-Link Documentation](https://www.segger.com/products/debug-probes/j-link/)
- [ADR-032: MCP Server for Hardware Test Stations](../../../ADR-032.md)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
