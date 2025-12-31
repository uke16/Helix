#!/bin/bash
# Helper commands for controller-038

# Check job status
check_job() {
    curl -s http://localhost:8001/helix/jobs/$1 | python3 -m json.tool
}

# List evolution projects
list_projects() {
    ls -la /home/aiuser01/helix-v4/projects/evolution/
}

# Run evolution pipeline
run_pipeline() {
    curl -X POST http://localhost:8001/helix/evolution/projects/$1/run
}
