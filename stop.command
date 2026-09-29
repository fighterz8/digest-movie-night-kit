#!/bin/bash
# Digest Movie Night Kit: stop (Mac).
cd "$(dirname "$0")" || exit 1
echo; echo "  Stopping the Digest Movie Night Kit..."
docker compose stop
echo; echo "  Stopped. Your movies and settings are kept. Double-click start to bring it back."
echo; read -r -p "  Press Enter to close. " _
