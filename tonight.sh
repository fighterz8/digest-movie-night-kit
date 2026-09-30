#!/bin/bash
# Digest Movie Night Kit: tonight's shopping trip (Linux and Mac). Checks the Movie Night list (if it's on) and
# searches for every movie on your wishlist that isn't downloaded yet. To run it every night at 1 AM, add this
# line with "crontab -e" (use this folder's real path):
#   0 1 * * * /bin/bash /path/to/digest-movie-night-kit-main/tonight.sh scheduled
cd "$(dirname "$0")" || exit 1
export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:$PATH"   # cron starts with a bare PATH
if [ "$1" = scheduled ]; then exec >> tonight-log.txt 2>&1; echo "=== $(date)"; fi
if ! docker info >/dev/null 2>&1; then
  echo "  Docker isn't running, so tonight's movies were skipped."
  exit 1
fi
docker compose run --rm --no-deps -T setup python3 /kit/setup.py tonight
