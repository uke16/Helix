# Iteration Log

This log documents all compatibility testing iterations for the MCP Base Server.

## Summary

| Iteration | Transport | Client | Result | Date |
|-----------|-----------|--------|--------|------|
| 1 | stdio | Claude Desktop | Pending | - |
| 2 | SSE | Claude Desktop (remote) | Pending | - |
| 3 | HTTP | ChatGPT | Pending | - |

---

## Iteration 1 - Pending

- **Transport:** stdio
- **Client:** Claude Desktop (local)
- **Result:** Pending
- **Error:** -
- **Fix:** -

### Test Steps

1. Configure Claude Desktop:
   ```json
   {
     "mcpServers": {
       "helix-base": {
         "command": "python",
         "args": ["/path/to/server.py", "stdio"]
       }
     }
   }
   ```
2. Restart Claude Desktop
3. Call `echo("test")` tool
4. Call `add(2, 3)` tool
5. Call `server_info()` tool

---

## Iteration 2 - Pending

- **Transport:** SSE
- **Client:** Claude Desktop (remote)
- **Result:** Pending
- **Error:** -
- **Fix:** -

### Test Steps

1. Start server: `python server.py sse`
2. Configure Claude Desktop with SSE URL
3. Test tool calls

---

## Iteration 3 - Pending

- **Transport:** HTTP (Streamable)
- **Client:** ChatGPT (Developer Mode)
- **Result:** Pending
- **Error:** -
- **Fix:** -

### Test Steps

1. Start server: `python server.py http`
2. Configure ChatGPT with MCP endpoint URL
3. Test tool calls

---

## Notes

- Use MCP Inspector (`npx @modelcontextprotocol/inspector`) for debugging
- Schema issues are common - check JSON-RPC format carefully
- FastMCP 2.0 handles most transport details automatically
