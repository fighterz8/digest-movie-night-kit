#!/bin/bash
# Digest Movie Night Kit: start (Linux). Run ./start.sh
cd "$(dirname "$0")" || exit 1
echo; echo "  Digest Movie Night Kit"; echo "  ======================"; echo

if ! docker info >/dev/null 2>&1; then
  echo "  Docker isn't running, or your user can't use it yet (add yourself to the docker group, then log in again)."
  exit 1
fi
if grep -q '^PASSWORD=change-me' settings.txt; then
  echo "  First, pick a password: edit the PASSWORD line in settings.txt, save it, then run ./start.sh again."
  exit 1
fi

export PUID PGID
PUID="$(id -u)"; PGID="$(id -g)"   # downloaded files belong to you, not root
mkdir -p media/movies media/downloads
# Jellyfin skips an empty movies folder (so the first movie wouldn't show up); this note keeps it non-empty.
[ -f media/movies/README.txt ] || echo "Your movies appear here, one folder per film. Radarr names them, so leave the names as they are." > media/movies/README.txt
echo "  Starting the apps. The first time takes a few minutes while they download..."
docker compose up -d || { echo "  Something went wrong starting the apps. The messages above say why."; exit 1; }
echo; echo "  Connecting everything..."
if ! docker compose wait setup >/dev/null; then
  echo "  Setup hit a problem. Here's what it said:"
  docker compose logs --no-log-prefix --tail 15 setup
  exit 1
fi

IP=$(hostname -I 2>/dev/null | awk '{print $1}')
echo; echo "  READY!"; echo
echo "    Add movies, in Radarr:   http://localhost:7878"
echo "    Watch, in Jellyfin:      http://localhost:8096"
[ -n "$IP" ] && echo "    On your TV or phone:     http://$IP:8096"
echo; echo "  Your movies are saved in $PWD/media/movies"
command -v xdg-open >/dev/null && { xdg-open "http://localhost:7878" >/dev/null 2>&1 & xdg-open "http://localhost:8096" >/dev/null 2>&1 & }
exit 0
