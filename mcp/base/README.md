# MCP Base Server

Minimal MCP server for compatibility testing with Claude Desktop and ChatGPT.

## Overview

This server provides a transport-agnostic MCP implementation using FastMCP 2.0.
It serves as the foundation for the hardware-specific MCP server (ADR-032).

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Local (stdio) - Claude Desktop

```bash
python server.py stdio
```

Claude Desktop config (`~/.config/claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "helix-base": {
      "command": "python",
      "args": ["/path/to/mcp/base/server.py", "stdio"]
    }
  }
}
```

### Remote (SSE) - Legacy

```bash
python server.py sse
```

Server starts on `http://0.0.0.0:8000`.

### Remote (HTTP) - Streamable HTTP (Recommended)

```bash
python server.py http
```

Server starts on `http://0.0.0.0:8000/mcp`.

## Available Tools

| Tool | Description |
|------|-------------|
| `echo(message)` | Echo a message back - connectivity test |
| `add(a, b)` | Add two numbers - execution test |
| `server_info()` | Get server metadata |

## Testing

### MCP Inspector

```bash
npx @modelcontextprotocol/inspector
```

### Manual Test (stdio)

```bash
echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | python server.py stdio
```

## Compatibility

| Client | Transport | Status |
|--------|-----------|--------|
| Claude Desktop (local) | stdio | See ITERATION_LOG.md |
| Claude Desktop (remote) | SSE/HTTP | See ITERATION_LOG.md |
| ChatGPT (Developer Mode) | HTTP | See ITERATION_LOG.md |

## Related

- [ADR-032](../../ADR-032.md) - MCP Server for Hardware Test Stand Orchestration
- [ITERATION_LOG.md](ITERATION_LOG.md) - Compatibility test results
