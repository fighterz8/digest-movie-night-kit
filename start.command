#!/bin/bash
# Digest Movie Night Kit: start (Mac). Double-click it. The first time, right-click it and choose Open.
cd "$(dirname "$0")" || exit 1
done_msg() { echo; read -r -p "  Press Enter to close. " _; exit "$1"; }
echo; echo "  Digest Movie Night Kit"; echo "  ======================"; echo

if ! docker info >/dev/null 2>&1; then
  echo "  Docker Desktop isn't running yet. Open it, wait until it says it's running, then start again."
  done_msg 1
fi
if grep -q '^PASSWORD=change-me' settings.txt; then
  echo "  First, pick a password: settings.txt is opening. Change the PASSWORD line, save it, then start again."
  open -e settings.txt
  done_msg 1
fi
case "$PWD" in
  *"Mobile Documents"*|*CloudStorage*)
    echo "  This folder is in iCloud Drive or another cloud folder, so your movies would upload there."
    echo "  Move the whole folder somewhere else (your home folder is fine), then start again."
    done_msg 1;;
esac

mkdir -p media/movies media/downloads
# Jellyfin skips an empty movies folder (so the first movie wouldn't show up); this note keeps it non-empty.
[ -f media/movies/README.txt ] || echo "Your movies appear here, one folder per film. Radarr names them, so leave the names as they are." > media/movies/README.txt
echo "  Starting the apps. The first time takes a few minutes while they download..."
docker compose up -d || { echo "  Something went wrong starting the apps. The messages above say why."; done_msg 1; }
echo; echo "  Connecting everything..."
if ! docker compose wait setup >/dev/null; then
  echo "  Setup hit a problem. Here's what it said:"
  docker compose logs --no-log-prefix --tail 15 setup
  done_msg 1
fi

IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null)
echo; echo "  READY!"; echo
echo "    Add movies, in Radarr:   http://localhost:7878"
echo "    Watch, in Jellyfin:      http://localhost:8096"
[ -n "$IP" ] && echo "    On your TV or phone:     http://$IP:8096"
echo; echo "  Your movies are saved in $PWD/media/movies"
open "http://localhost:7878"
open "http://localhost:8096"
done_msg 0
