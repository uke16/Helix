# MCP Server Deployment Log

ADR-032: Phase 4 - Deploy to Test System

## Deployment Summary

| Component | Status | Port | Transport |
|-----------|--------|------|-----------|
| helix-base | Deployed | 8088 | SSE |
| helix-hardware | Deployed | 8089 | SSE |

## Deployment Date

2025-12-30

## Environment

- **OS:** Linux ai-vm 6.8.0-87-generic (Ubuntu)
- **Python:** 3.12.3
- **FastMCP:** 2.14.1
- **MCP SDK:** 1.25.0

## Base Server (helix-base)

### Deployment Details

- **Port:** 8088
- **URL:** http://localhost:8088/sse
- **Transport:** SSE (Server-Sent Events)
- **PID:** Active

### Tools Available

| Tool | Description | Status |
|------|-------------|--------|
| `echo` | Echo a message back | Verified |
| `add` | Add two numbers | Verified |
| `server_info` | Get server information | Verified |

### Verification Tests

```
Test: echo tool
Input: {"message": "DEPLOY"}
Output: "Echo: DEPLOY"
Result: PASSED

Test: add tool
Input: {"a": 100, "b": 88}
Output: 188
Result: PASSED
```

## Hardware Server (helix-hardware)

### Deployment Details

- **Port:** 8089
- **URL:** http://localhost:8089/sse
- **Transport:** SSE (Server-Sent Events)
- **PID:** Active

### Tools Available

| Tool | Description | Status |
|------|-------------|--------|
| `list_stations` | List available hardware stations | Verified |
| `station_status` | Get station details | Verified |
| `station_acquire` | Acquire exclusive access | Verified |
| `station_release` | Release exclusive access | Verified |

### Verification Tests

```
Test: list_stations
Output: 3 stations found (station-1, station-2, station-dev)
Result: PASSED

Test: station_acquire
Input: {"station": "station-1", "session_id": "deploy-test"}
Output: "Lock acquired on station-1 for 300s"
Result: PASSED

Test: station_release
Input: {"station": "station-1", "session_id": "deploy-test"}
Output: "Lock released on station-1"
Result: PASSED
```

## Configuration Notes

### Port Selection

Default port 8000 is occupied by HELIX server. Deployment uses:
- Port 8088 for base server
- Port 8089 for hardware server

### Transport Mode

SSE (Server-Sent Events) transport was chosen for:
- Claude Desktop (remote) compatibility
- ChatGPT (Developer Mode) compatibility
- HTTP-based access for external clients

### Stations Configured

| Station | Description | Target | Status |
|---------|-------------|--------|--------|
| station-1 | Primary FPGA Test Station | nRF5340 (Cortex-M33) | Available |
| station-2 | Secondary FPGA Test Station | nRF5340 (Cortex-M33) | Available |
| station-dev | Development Station | Simulator | Available |

## Deployment Commands

### Start Base Server

```bash
cd /home/aiuser01/helix-v4/mcp/base
python3 -c "
from fastmcp import FastMCP

mcp = FastMCP(name='helix-base', version='0.1.0')

@mcp.tool
def echo(message: str) -> str:
    return f'Echo: {message}'

@mcp.tool
def add(a: int, b: int) -> int:
    return a + b

@mcp.tool
def server_info() -> dict:
    return {'name': 'helix-base', 'version': '0.1.0', 'status': 'ready'}

mcp.run(transport='sse', host='0.0.0.0', port=8088)
"
```

### Start Hardware Server

```bash
cd /home/aiuser01/helix-v4/mcp/hardware
python3 server.py sse  # Note: Requires port override to 8089
```

## Quality Gate

Per phases.yaml criteria:

- [x] DEPLOY_LOG.md created
- [x] Base server deployed and verified
- [x] Hardware server deployed and verified
- [x] Tools discoverable via MCP client
- [x] Tool calls execute correctly
- [x] Locking mechanism works

## Next Steps

Phase 5 (Production Integration):
- [ ] Configure persistent systemd services
- [ ] Set up reverse proxy (nginx/caddy) for HTTPS
- [ ] Configure authentication (API keys or OAuth)
- [ ] Set up monitoring and alerting
- [ ] Document Claude Desktop / ChatGPT connection steps

## Issues Encountered

### Port Conflict

- **Issue:** Default port 8000 occupied by HELIX API server
- **Resolution:** Deployed on ports 8088/8089
- **Note:** Production deployment should use dedicated ports or reverse proxy

### FastMCP Port Override

- **Issue:** FastMCP 2.14.1 requires explicit port parameter
- **Resolution:** Pass port as keyword argument to `mcp.run()`
