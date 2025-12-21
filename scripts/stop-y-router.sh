#!/bin/bash
# HELIX v4 - y-router stoppen

cd /home/aiuser01/helix-v4/y-router
docker compose down
echo "✅ y-router gestoppt"
