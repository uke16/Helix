---
adr_id: "033"
title: MCP Blueprint Server - Modulare Remote-fähige Architektur
status: Proposed

project_type: external
component_type: SERVICE
classification: NEW
change_scope: major

files:
  create:
    - mcp/blueprint/server.py
    - mcp/blueprint/auth/oauth.py
    - mcp/blueprint/auth/__init__.py
    - mcp/blueprint/config.py
    - mcp/blueprint/__init__.py
    - mcp/services/__init__.py
    - mcp/services/helix/service.py
    - mcp/services/helix/__init__.py
    - mcp/services/consultant/service.py
    - mcp/services/consultant/__init__.py
    - mcp/composed/fraba_internal.py
    - mcp/composed/fraba_external.py
    - mcp/composed/__init__.py
    - mcp/config/internal.yaml
    - mcp/config/external.yaml
  modify:
    - mcp/services/hardware/service.py  # Refactored from mcp-backup-adr032
  docs:
    - mcp/blueprint/README.md
    - mcp/services/README.md
    - docs/MCP-ARCHITECTURE.md

depends_on:
  - ADR-032
---

# ADR-033: MCP Blueprint Server - Modulare Remote-fähige Architektur

## Status
📋 Proposed

## Kontext

### Ausgangslage
Mit ADR-032 wurde ein MCP Server für Hardware-Teststände entwickelt. Dieser funktioniert, aber:

1. **Nicht modular**: Hardware-Tools sind direkt im Server, nicht als mountbarer Service
2. **Keine Auth**: Kein OAuth/Bearer Token Support für externe Nutzung
3. **Single-Purpose**: Nur für Hardware, nicht erweiterbar für HELIX/Consultant/PDM

### Ziel
Ein "Raw Blueprint" MCP Server der:

- **Remote-fähig** ist (HTTPS, OAuth 2.1)
- Mit **Claude Web** und **ChatGPT Web** funktioniert
- **Modulare Services** über `mount()` registriert
- **Intern/Extern** über Config gesteuert wird
- **Wiederverwendbar** für andere Projekte ist

### Use Cases

| Client | Use Case | Services |
|--------|----------|----------|
| Claude Desktop (lokal) | Hardware-Debugging | Hardware, HELIX |
| Claude Web (remote) | Projekt-Status, Skill-Suche | HELIX, Consultant |
| ChatGPT Web (remote) | Skill-Dokumentation abfragen | Consultant |
| HELIX Orchestrator | Phase-Status über MCP | HELIX (self-referential) |

## Entscheidung

### Drei-Schichten-Architektur

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     Layer 3: Composed Servers                            │
│  ┌──────────────────────┐  ┌──────────────────────┐                     │
│  │  fraba-internal      │  │  fraba-external      │                     │
│  │  ├─ Hardware ✓       │  │  ├─ HELIX ✓          │                     │
│  │  ├─ HELIX ✓          │  │  ├─ Consultant ✓     │                     │
│  │  ├─ Consultant ✓     │  │  │  (NO Hardware!)   │                     │
│  │  └─ PDM (später)     │  │  └─ OAuth 2.1        │                     │
│  │  No Auth             │  │                      │                     │
│  └──────────────────────┘  └──────────────────────┘                     │
└──────────────────────────────────────────────────────────────────────────┘
                              │ mount()
┌─────────────────────────────────────────────────────────────────────────┐
│                     Layer 2: Service Layer                               │
│  ┌───────────────┐  ┌───────────────┐  ┌────────────────┐  ┌──────────┐│
│  │HardwareService│  │ HELIXService  │  │ConsultantService│ │PDMService││
│  │(from ADR-032) │  │               │  │                 │ │(später)  ││
│  │               │  │               │  │                 │ │          ││
│  │ station_*     │  │ phase_status  │  │ skill_search    │ │          ││
│  │ locking       │  │ list_jobs     │  │ adr_search      │ │          ││
│  │ audit         │  │ run_quality_  │  │ code_context    │ │          ││
│  │               │  │   gate        │  │   (optional)    │ │          ││
│  │               │  │ escalate_to_  │  │                 │ │          ││
│  │               │  │   consultant  │  │                 │ │          ││
│  └───────────────┘  └───────────────┘  └─────────────────┘  └──────────┘│
└──────────────────────────────────────────────────────────────────────────┘
                              │ extends
┌─────────────────────────────────────────────────────────────────────────┐
│                     Layer 1: Blueprint Base                              │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │  BlueprintMCP(FastMCP)                                               ││
│  │  ├─ Multi-Transport: stdio, SSE, streamable-http                    ││
│  │  ├─ Optional HTTPS/TLS                                               ││
│  │  ├─ Optional OAuth 2.1 Middleware                                    ││
│  │  └─ Service mount() API                                              ││
│  └─────────────────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────────────┘
```

### Auth-Matrix

| Server | Network | Auth | Exposed Services |
|--------|---------|------|------------------|
| fraba-internal | LAN/VPN | None | Hardware, HELIX, Consultant, PDM |
| fraba-external | Internet | OAuth 2.1 | HELIX, Consultant (NO Hardware!) |

### Transport Support

| Transport | Use Case | Auth Support |
|-----------|----------|--------------|
| stdio | Claude Desktop (lokal) | N/A (trusted) |
| SSE | Legacy remote clients | Bearer Token |
| streamable-http | Claude Web, ChatGPT | OAuth 2.1 |

## Implementation

### Layer 1: Blueprint Base

`mcp/blueprint/server.py`:

```python
"""Blueprint MCP Server - Remote-ready base with optional auth.

ADR-033: MCP Blueprint Server Architecture
"""
from typing import Callable, Optional
from fastmcp import FastMCP
from .auth.oauth import OAuthMiddleware
from .config import BlueprintConfig


class BlueprintMCP(FastMCP):
    """Extended FastMCP with service mounting and optional auth."""

    def __init__(
        self,
        name: str,
        version: str = "0.1.0",
        config: Optional[BlueprintConfig] = None,
    ):
        super().__init__(name=name, version=version)
        self.config = config or BlueprintConfig()
        self._mounted_services: dict[str, FastMCP] = {}

        if self.config.auth_enabled:
            self._setup_auth()

    def _setup_auth(self) -> None:
        """Configure OAuth 2.1 middleware if enabled."""
        self.auth = OAuthMiddleware(
            issuer=self.config.oauth_issuer,
            audience=self.config.oauth_audience,
            required_scopes=self.config.oauth_scopes,
        )

    def mount(self, prefix: str, service: FastMCP) -> None:
        """Mount a service with prefixed tool names.

        Args:
            prefix: Prefix for tool names (e.g., "hardware" -> "hardware_*")
            service: FastMCP service instance to mount

        Example:
            >>> server.mount("hardware", hardware_service)
            # Tools become: hardware_station_acquire, hardware_list_stations, etc.
        """
        self._mounted_services[prefix] = service

        # Register all tools from service with prefix
        for tool_name, tool_func in service._tools.items():
            prefixed_name = f"{prefix}_{tool_name}"
            self.tool(name=prefixed_name)(tool_func)

    def run(
        self,
        transport: str = "stdio",
        host: str = "0.0.0.0",
        port: int = 8000,
        path: str = "/mcp",
        ssl_cert: Optional[str] = None,
        ssl_key: Optional[str] = None,
    ) -> None:
        """Run the server with specified transport.

        Args:
            transport: One of "stdio", "sse", "http"
            host: Bind address for network transports
            port: Port for network transports
            path: URL path for HTTP transport
            ssl_cert: Path to SSL certificate (enables HTTPS)
            ssl_key: Path to SSL key
        """
        if transport == "stdio":
            super().run(transport="stdio")
        elif transport == "sse":
            super().run(transport="sse", host=host, port=port)
        elif transport == "http":
            # TODO: Add SSL support when FastMCP supports it
            super().run(transport="http", host=host, port=port, path=path)
        else:
            raise ValueError(f"Unknown transport: {transport}")
```

`mcp/blueprint/auth/oauth.py`:

```python
"""OAuth 2.1 Middleware for MCP Blueprint.

Supports Bearer Token validation for remote MCP servers.
"""
from dataclasses import dataclass
from typing import Optional
import httpx


@dataclass
class OAuthConfig:
    """OAuth 2.1 configuration."""
    issuer: str
    audience: str
    required_scopes: list[str]
    jwks_uri: Optional[str] = None  # Auto-discovered from issuer


class OAuthMiddleware:
    """OAuth 2.1 token validation middleware."""

    def __init__(
        self,
        issuer: str,
        audience: str,
        required_scopes: Optional[list[str]] = None,
    ):
        self.issuer = issuer
        self.audience = audience
        self.required_scopes = required_scopes or []
        self._jwks_client: Optional[httpx.AsyncClient] = None

    async def validate_token(self, token: str) -> dict:
        """Validate a Bearer token and return claims.

        Args:
            token: JWT Bearer token

        Returns:
            Token claims if valid

        Raises:
            AuthError: If token is invalid
        """
        # Implementation depends on OAuth provider
        # For now, placeholder for JWT validation
        import jwt

        # Fetch JWKS from issuer
        jwks_uri = f"{self.issuer}/.well-known/jwks.json"

        async with httpx.AsyncClient() as client:
            jwks = await client.get(jwks_uri)
            keys = jwks.json()["keys"]

        # Validate token (simplified)
        claims = jwt.decode(
            token,
            keys[0],  # Use first key (simplified)
            algorithms=["RS256"],
            audience=self.audience,
            issuer=self.issuer,
        )

        # Check scopes
        token_scopes = claims.get("scope", "").split()
        for required in self.required_scopes:
            if required not in token_scopes:
                raise PermissionError(f"Missing scope: {required}")

        return claims
```

`mcp/blueprint/config.py`:

```python
"""Blueprint configuration."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import yaml


@dataclass
class BlueprintConfig:
    """Configuration for Blueprint MCP Server."""

    # Auth settings
    auth_enabled: bool = False
    oauth_issuer: Optional[str] = None
    oauth_audience: Optional[str] = None
    oauth_scopes: list[str] = field(default_factory=list)

    # TLS settings
    ssl_enabled: bool = False
    ssl_cert: Optional[str] = None
    ssl_key: Optional[str] = None

    # Service settings
    enabled_services: list[str] = field(default_factory=list)

    @classmethod
    def from_yaml(cls, path: Path) -> "BlueprintConfig":
        """Load configuration from YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**data)
```

### Layer 2: Services

#### HELIX Service

`mcp/services/helix/service.py`:

```python
"""HELIX Orchestrator MCP Service.

Exposes HELIX orchestration capabilities as MCP tools.

ADR-033: MCP Blueprint Server Architecture
"""
from fastmcp import FastMCP
import httpx

helix_service = FastMCP(name="helix-service", version="0.1.0")

# HELIX API base URL (configurable)
HELIX_API = "http://localhost:8001"


@helix_service.tool
async def phase_status(project: str) -> dict:
    """Get current phase status of a HELIX project.

    Args:
        project: Project path (e.g., "projects/evolution/my-feature")

    Returns:
        Phase status including current phase, completion, and any errors
    """
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{HELIX_API}/helix/projects/{project}/status")
        return r.json()


@helix_service.tool
async def list_jobs(status_filter: str = None) -> list:
    """List all HELIX jobs.

    Args:
        status_filter: Optional filter by status (running, completed, failed)

    Returns:
        List of jobs with their IDs and statuses
    """
    async with httpx.AsyncClient() as client:
        params = {"status": status_filter} if status_filter else {}
        r = await client.get(f"{HELIX_API}/helix/jobs", params=params)
        return r.json()


@helix_service.tool
async def run_quality_gate(project: str, phase: int) -> dict:
    """Execute quality gate for a specific phase.

    Args:
        project: Project path
        phase: Phase number to validate

    Returns:
        Quality gate result with pass/fail and any issues
    """
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{HELIX_API}/helix/projects/{project}/phases/{phase}/quality-gate"
        )
        return r.json()


@helix_service.tool
async def escalate_to_consultant(project: str, issue: str) -> str:
    """Escalate an issue to the consultant for human review.

    Args:
        project: Project path
        issue: Description of the issue requiring escalation

    Returns:
        Escalation confirmation with ticket/session ID
    """
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{HELIX_API}/helix/escalate",
            json={"project": project, "issue": issue}
        )
        data = r.json()
        return f"Escalation created: {data.get('session_id')}"
```

#### Consultant/RAG Service

`mcp/services/consultant/service.py`:

```python
"""Consultant RAG MCP Service.

Provides semantic search over HELIX skills, ADRs, and code.

ADR-033: MCP Blueprint Server Architecture
"""
from fastmcp import FastMCP
from pathlib import Path
import httpx

consultant_service = FastMCP(name="consultant-service", version="0.1.0")

# RAG API endpoint (LiteLLM or similar)
RAG_API = "http://localhost:8002"
HELIX_ROOT = Path("/home/aiuser01/helix-v4")


@consultant_service.tool
async def skill_search(query: str, limit: int = 5) -> list:
    """Semantic search over HELIX skills.

    Args:
        query: Natural language search query
        limit: Maximum number of results (default 5)

    Returns:
        List of matching skills with relevance scores and excerpts
    """
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{RAG_API}/search",
            json={
                "query": query,
                "collection": "skills",
                "limit": limit,
            }
        )
        return r.json()


@consultant_service.tool
async def adr_search(query: str, status: str = None, limit: int = 10) -> list:
    """Search ADRs by keyword or semantic similarity.

    Args:
        query: Search query (keyword or natural language)
        status: Optional filter by status (Proposed, Accepted, Integrated)
        limit: Maximum number of results (default 10)

    Returns:
        List of matching ADRs with IDs, titles, and relevance
    """
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{RAG_API}/search",
            json={
                "query": query,
                "collection": "adrs",
                "filters": {"status": status} if status else {},
                "limit": limit,
            }
        )
        return r.json()


@consultant_service.tool
def list_skills() -> list:
    """List all available HELIX skills.

    Returns:
        List of skill names and their paths
    """
    skills_dir = HELIX_ROOT / "skills"
    skills = []

    for skill_file in skills_dir.rglob("SKILL.md"):
        rel_path = skill_file.relative_to(skills_dir)
        skill_name = str(rel_path.parent)
        skills.append({
            "name": skill_name,
            "path": str(skill_file),
        })

    return skills


@consultant_service.tool
def read_skill(skill_name: str) -> str:
    """Read a specific skill's content.

    Args:
        skill_name: Skill name (e.g., "helix/adr", "pdm")

    Returns:
        Full markdown content of the skill
    """
    skill_path = HELIX_ROOT / "skills" / skill_name / "SKILL.md"

    if not skill_path.exists():
        return f"Skill not found: {skill_name}"

    return skill_path.read_text()
```

### Layer 3: Composed Servers

`mcp/composed/fraba_internal.py`:

```python
"""Fraba Internal MCP Server - All services, no auth.

For use within trusted network (LAN/VPN).

ADR-033: MCP Blueprint Server Architecture
"""
import sys
from pathlib import Path

# Add mcp to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mcp.blueprint.server import BlueprintMCP
from mcp.blueprint.config import BlueprintConfig
from mcp.services.hardware.service import hardware_service
from mcp.services.helix.service import helix_service
from mcp.services.consultant.service import consultant_service


def create_server() -> BlueprintMCP:
    """Create internal MCP server with all services."""
    config = BlueprintConfig(
        auth_enabled=False,
        enabled_services=["hardware", "helix", "consultant"],
    )

    server = BlueprintMCP(
        name="fraba-internal",
        version="0.1.0",
        config=config,
    )

    # Mount all services
    server.mount("hardware", hardware_service)
    server.mount("helix", helix_service)
    server.mount("consultant", consultant_service)

    return server


if __name__ == "__main__":
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"
    server = create_server()

    if transport == "stdio":
        server.run(transport="stdio")
    elif transport == "sse":
        server.run(transport="sse", host="0.0.0.0", port=8000)
    elif transport == "http":
        server.run(transport="http", host="0.0.0.0", port=8000, path="/mcp")
```

`mcp/composed/fraba_external.py`:

```python
"""Fraba External MCP Server - Limited services with OAuth.

For use over public internet with Claude Web / ChatGPT.

ADR-033: MCP Blueprint Server Architecture
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mcp.blueprint.server import BlueprintMCP
from mcp.blueprint.config import BlueprintConfig
from mcp.services.helix.service import helix_service
from mcp.services.consultant.service import consultant_service


def create_server() -> BlueprintMCP:
    """Create external MCP server with OAuth and limited services."""
    config = BlueprintConfig(
        auth_enabled=True,
        oauth_issuer="https://auth.fraba.com",  # Configure appropriately
        oauth_audience="helix-mcp",
        oauth_scopes=["helix:read", "consultant:read"],
        enabled_services=["helix", "consultant"],
        # Note: Hardware is NOT exposed externally!
    )

    server = BlueprintMCP(
        name="fraba-external",
        version="0.1.0",
        config=config,
    )

    # Mount only safe services (NO HARDWARE!)
    server.mount("helix", helix_service)
    server.mount("consultant", consultant_service)

    return server


if __name__ == "__main__":
    transport = sys.argv[1] if len(sys.argv) > 1 else "http"
    server = create_server()

    # External always uses HTTP with HTTPS recommended
    server.run(
        transport="http",
        host="0.0.0.0",
        port=8443,
        path="/mcp",
        # ssl_cert="/etc/ssl/certs/helix.crt",
        # ssl_key="/etc/ssl/private/helix.key",
    )
```

### Config Files

`mcp/config/internal.yaml`:

```yaml
# Internal MCP Server Configuration
# Used within trusted network (LAN/VPN)

auth_enabled: false

enabled_services:
  - hardware
  - helix
  - consultant
  # - pdm  # Enable when ready

# Hardware-specific settings
hardware:
  stations_config: /home/aiuser01/helix-v4/mcp/services/hardware/config.yaml
  audit_log: /var/log/helix/hardware-audit.jsonl

# HELIX API connection
helix:
  api_url: http://localhost:8001

# RAG/Consultant settings
consultant:
  rag_api: http://localhost:8002
  helix_root: /home/aiuser01/helix-v4
```

`mcp/config/external.yaml`:

```yaml
# External MCP Server Configuration
# Used over public internet with OAuth

auth_enabled: true

oauth:
  issuer: https://auth.fraba.com
  audience: helix-mcp
  required_scopes:
    - helix:read
    - consultant:read

ssl:
  enabled: true
  cert: /etc/ssl/certs/helix.crt
  key: /etc/ssl/private/helix.key

enabled_services:
  - helix
  - consultant
  # Hardware is NEVER exposed externally!

# HELIX API connection (internal)
helix:
  api_url: http://localhost:8001

# RAG/Consultant settings
consultant:
  rag_api: http://localhost:8002
  helix_root: /home/aiuser01/helix-v4
```

### Directory Structure

```
mcp/
├── blueprint/                 # Layer 1: Reusable Blueprint
│   ├── __init__.py
│   ├── server.py             # BlueprintMCP class
│   ├── config.py             # BlueprintConfig
│   ├── auth/
│   │   ├── __init__.py
│   │   └── oauth.py          # OAuth 2.1 middleware
│   └── README.md
│
├── services/                  # Layer 2: Mountable Services
│   ├── __init__.py
│   ├── README.md
│   ├── hardware/             # From ADR-032 (refactored)
│   │   ├── __init__.py
│   │   ├── service.py        # hardware_service FastMCP
│   │   ├── locking.py
│   │   ├── audit.py
│   │   └── config.yaml
│   ├── helix/                # NEW
│   │   ├── __init__.py
│   │   └── service.py        # helix_service FastMCP
│   └── consultant/           # NEW
│       ├── __init__.py
│       └── service.py        # consultant_service FastMCP
│
├── composed/                  # Layer 3: Ready-to-run Servers
│   ├── __init__.py
│   ├── fraba_internal.py     # All services, no auth
│   └── fraba_external.py     # Limited services, OAuth
│
└── config/
    ├── internal.yaml
    └── external.yaml
```

## Dokumentation

| Dokument | Änderung |
|----------|----------|
| `mcp/blueprint/README.md` | Blueprint usage and extension guide |
| `mcp/services/README.md` | How to create and mount services |
| `docs/MCP-ARCHITECTURE.md` | Overall MCP architecture in HELIX |
| `docs/ARCHITECTURE-MODULES.md` | Add MCP section |

## Akzeptanzkriterien

### Phase 0: Blueprint Base
- [ ] BlueprintMCP extends FastMCP with mount() API
- [ ] OAuth middleware can validate Bearer tokens
- [ ] Config loading from YAML works
- [ ] All three transports work (stdio, SSE, HTTP)

### Phase 1: Hardware Service Refactor
- [ ] Hardware service extracted from ADR-032 code
- [ ] All existing tools work via mount()
- [ ] Audit logging preserved

### Phase 2: HELIX Service
- [ ] phase_status returns correct data
- [ ] list_jobs queries HELIX API
- [ ] run_quality_gate triggers gate execution
- [ ] escalate_to_consultant creates escalation

### Phase 3: Consultant Service
- [ ] skill_search performs semantic search
- [ ] adr_search finds relevant ADRs
- [ ] list_skills enumerates all skills
- [ ] read_skill returns skill content

### Phase 4: Composed Servers
- [ ] fraba-internal works via stdio (Claude Desktop)
- [ ] fraba-internal works via SSE (remote test)
- [ ] fraba-external requires OAuth token
- [ ] fraba-external rejects hardware tool calls

### Phase 5: Integration Tests
- [ ] Claude Desktop (local) can use fraba-internal
- [ ] Claude Web can connect to fraba-external
- [ ] ChatGPT can connect to fraba-external
- [ ] HELIX API integration verified

## Konsequenzen

### Positiv
- **Modular**: Services können unabhängig entwickelt werden
- **Secure**: OAuth für externe Nutzung, Hardware nur intern
- **Reusable**: Blueprint kann für andere Projekte genutzt werden
- **Compatible**: Funktioniert mit Claude Desktop, Claude Web, ChatGPT

### Negativ
- **Komplexität**: Drei Schichten statt einem Server
- **OAuth Setup**: Initialer Aufwand für Auth-Provider
- **Dependencies**: FastMCP 2.x, httpx, PyJWT

### Risiken

| Risiko | Mitigation |
|--------|------------|
| FastMCP API Änderungen | Version pinning, Tests |
| OAuth Provider Downtime | Graceful degradation, Token caching |
| Service-Isolierung | Klare Trennungslinien, keine shared state |

## Referenzen

- [ADR-032: Hardware MCP Server](032-mcp-hardware-server.md)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [OAuth 2.1 Spec](https://oauth.net/2.1/)
- [MCP Protocol Spec](https://modelcontextprotocol.io/)
