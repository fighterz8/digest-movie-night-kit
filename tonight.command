#!/bin/bash
# Digest Movie Night Kit: tonight's shopping trip (Mac). Double-click it to run it now. To run it every night,
# schedule tonight.sh with cron (see the README).
cd "$(dirname "$0")" || exit 1
bash ./tonight.sh
echo; read -r -p "  Press Enter to close. " _
