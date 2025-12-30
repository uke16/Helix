#!/bin/bash
# Helper commands für Evolution Controller

# Start workflow
start() {
  curl -s -X POST http://localhost:8001/helix/execute \
    -H "Content-Type: application/json" \
    -d '{"project_path": "projects/evolution/mcp-server-032"}' | jq .
}

# Check job status
status() {
  curl -s http://localhost:8001/helix/jobs/$1 | jq .
}

# List all jobs
jobs() {
  curl -s http://localhost:8001/helix/jobs | jq .
}

# Deploy
deploy() {
  curl -s -X POST http://localhost:8001/helix/evolution/projects/mcp-server-032/deploy | jq .
}

# Validate
validate() {
  curl -s -X POST http://localhost:8001/helix/evolution/projects/mcp-server-032/validate | jq .
}

# Integrate
integrate() {
  curl -s -X POST http://localhost:8001/helix/evolution/projects/mcp-server-032/integrate | jq .
}

# Usage
echo "Commands: start, status <job_id>, jobs, deploy, validate, integrate"
echo "Example: source commands.sh && start"
