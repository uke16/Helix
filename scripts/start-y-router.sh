#!/bin/bash
# HELIX v4 - y-router starten (einmalig)

ROUTER_DIR="/home/aiuser01/helix-v4/y-router"

# Prüfen ob bereits läuft
if curl -s http://localhost:8787/ > /dev/null 2>&1; then
    echo "✅ y-router läuft bereits auf Port 8787"
    exit 0
fi

# Starten
cd "$ROUTER_DIR"
docker compose up -d

# Warten
echo "⏳ Warte auf y-router..."
for i in {1..30}; do
    if curl -s http://localhost:8787/ > /dev/null 2>&1; then
        echo "✅ y-router gestartet auf http://localhost:8787"
        exit 0
    fi
    sleep 1
done

echo "❌ y-router konnte nicht gestartet werden"
exit 1
