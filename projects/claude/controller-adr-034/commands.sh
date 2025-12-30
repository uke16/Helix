#!/bin/bash
# Helper commands für Controller ADR-034

API="http://localhost:8001"
PROJECT="consultant-refactor-034"

case "$1" in
  execute)
    curl -X POST "$API/helix/execute" \
      -H "Content-Type: application/json" \
      -d "{\"project_path\": \"projects/evolution/$PROJECT\"}"
    ;;
  status)
    curl "$API/helix/jobs/$2"
    ;;
  deploy)
    curl -X POST "$API/helix/evolution/projects/$PROJECT/deploy"
    ;;
  validate)
    curl -X POST "$API/helix/evolution/projects/$PROJECT/validate"
    ;;
  integrate)
    curl -X POST "$API/helix/evolution/projects/$PROJECT/integrate"
    ;;
  *)
    echo "Usage: $0 {execute|status <job_id>|deploy|validate|integrate}"
    ;;
esac
