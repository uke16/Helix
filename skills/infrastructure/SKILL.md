# Infrastructure Domain

## Overview

HELIX v4 infrastructure includes:
- Docker containers
- PostgreSQL database
- Vector stores (Qdrant)
- Graph database (Neo4j)
- Redis cache
- Proxmox VMs

## Docker Setup

### HELIX Services
```yaml
services:
  helix-api:     # FastAPI REST API
  helix-postgres: # Job/project state
```

### Supporting Services
```yaml
services:
  qdrant:        # Vector search
  neo4j:         # Graph database
  redis:         # Cache/queue
  minio:         # Object storage
```

## VM Architecture

```
Proxmox Host
├── ai-vm (HELIX development)
│   ├── Docker containers
│   └── Claude Code CLI
└── other VMs...
```

## Networking

- Internal: Docker bridge network
- External: Reverse proxy (nginx/traefik)
- Ports: 8100 (API), 5434 (Postgres)

## Deployment

1. Clone repository
2. Configure `.env`
3. `docker compose up -d`
4. Verify health checks

## Monitoring

- Container logs: `docker logs`
- Metrics: Prometheus/Grafana (optional)
- Health endpoints: `/health`
