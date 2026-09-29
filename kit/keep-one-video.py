#!/usr/bin/env python3
"""Digest Movie Night Kit helper, run by qBittorrent every time a download is added.

Internet Archive uploads often hold every copy of a film (a DVD image, Ogg, low-res MP4s...). This keeps only the
biggest playable video, then renames it "<Title> (<Year>)" from the Archive's own record, so Radarr recognises it
(Archive files have names like Night.mp4 inside a folder like night_of_the_living_dead_dvd).
qBittorrent setting (Downloads): Run external program on torrent added:  python3 /config/keep-one-video.py "%I"
"""
import json, os, re, sys, time, urllib.parse, urllib.request

API = "http://127.0.0.1:8080/api/v2"  # works without a password because qBittorrent trusts its own address
VIDEO = (".mp4", ".mkv", ".m4v", ".avi", ".mov")


def call(path, data=None):
    req = urllib.request.Request(API + path, data=urllib.parse.urlencode(data).encode() if data else None)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode()


h = sys.argv[1]
files = []
for _ in range(60):  # a magnet link needs a moment to fetch the file list
    files = json.loads(call(f"/torrents/files?hash={h}") or "[]")
    if files:
        break
    time.sleep(2)
videos = [f for f in files if f["name"].lower().endswith(VIDEO) and "512kb" not in f["name"].lower()]
if not videos:
    sys.exit(0)
keep = max(videos, key=lambda f: f["size"])
skip = [str(f["index"]) for f in files if f["index"] != keep["index"]]
if skip:
    call("/torrents/filePrio", {"hash": h, "id": "|".join(skip), "priority": 0})
print(f"kept {keep['name']} ({keep['size'] / 1e6:.0f} MB), skipped {len(skip)} other files")

folder, name = os.path.split(keep["name"])
identifier = keep["name"].split("/")[0]
try:
    url = f"https://archive.org/metadata/{urllib.parse.quote(identifier)}/metadata"
    meta = json.load(urllib.request.urlopen(url, timeout=20)).get("result", {})
except Exception:
    meta = {}  # not an Internet Archive download (or the Archive is down): leave the name alone
title = meta.get("title")
year = str(meta.get("year") or meta.get("date") or "")[:4]
if title and year.isdigit():
    title = re.sub(r"\s*\(?\b%s\b\)?" % year, "", re.sub(r'[\\/:*?"<>|]', "", title)).strip()
    new = f"{title} ({year}){os.path.splitext(name)[1]}"
    new = f"{folder}/{new}" if folder else new
    if new != keep["name"]:
        call("/torrents/renameFile", {"hash": h, "oldPath": keep["name"], "newPath": new})
        print(f"renamed to {new}")
