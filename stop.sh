#!/bin/bash
# Digest Movie Night Kit: stop (Linux).
cd "$(dirname "$0")" || exit 1
echo "  Stopping the Digest Movie Night Kit..."
docker compose stop
echo "  Stopped. Your movies and settings are kept. Run ./start.sh to bring it back."
