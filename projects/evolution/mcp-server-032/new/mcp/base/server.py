"""MCP Base Server - Compatible with Claude + ChatGPT.

This server provides a minimal, transport-agnostic MCP implementation
using FastMCP. It supports stdio, SSE, and HTTP transports for compatibility
with Claude Desktop (local + remote) and ChatGPT (Developer Mode).

ADR-032: MCP Server for Hardware Test Stand Orchestration
"""
from fastmcp import FastMCP

mcp = FastMCP(
    name="helix-base",
    version="0.1.0",
)


@mcp.tool
def echo(message: str) -> str:
    """Echo a message back. Use this to test connectivity."""
    return f"Echo: {message}"


@mcp.tool
def add(a: int, b: int) -> int:
    """Add two numbers. Use this to test tool execution."""
    return a + b


@mcp.tool
def server_info() -> dict:
    """Get server information."""
    return {
        "name": "helix-base",
        "version": "0.1.0",
        "transports": ["stdio", "sse", "http"],
        "status": "ready"
    }


if __name__ == "__main__":
    import sys

    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"

    if transport == "stdio":
        mcp.run(transport="stdio")
    elif transport == "sse":
        mcp.run(transport="sse", host="0.0.0.0", port=8000)
    elif transport == "http":
        mcp.run(transport="http", host="0.0.0.0", port=8000, path="/mcp")
    else:
        print(f"Unknown transport: {transport}")
        print("Usage: python server.py [stdio|sse|http]")
        sys.exit(1)
