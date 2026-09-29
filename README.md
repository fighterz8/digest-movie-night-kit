# Digest Movie Night Kit

Your own Netflix of free, public-domain movies. Add a film to a wishlist; it downloads from the Internet Archive on its own and shows up in Jellyfin with its poster, ready for your TV.

From the Mr Digest video.

## Download
Click the green **Code** button above, then **Download ZIP**. Unzip it somewhere with plenty of space (not inside OneDrive or iCloud), then follow [START-HERE.txt](START-HERE.txt). You'll need [Docker Desktop](https://www.docker.com/products/docker-desktop/), which is free for personal use.

**On Windows, turn on WSL before installing Docker Desktop:** run `wsl --install --no-distribution` in PowerShell as administrator, then restart. Without it, Docker Desktop's default install shows "Virtualization support not detected" even on PCs where virtualization is fine.

## What's inside
| App | Job | Where |
|---|---|---|
| [Jellyfin](https://jellyfin.org) | your Netflix: the app you watch on | `http://localhost:8096`, and on your home network for TVs |
| [Radarr](https://radarr.video) | the robot with your wishlist | `http://localhost:7878`, this computer only |
| [qBittorrent](https://www.qbittorrent.org) | the downloader | inside the kit only |
| [Jackett](https://github.com/Jackett/Jackett) | searches the Internet Archive | inside the kit only |

`start` runs everything with Docker Compose, then a one-shot `setup` step wires the apps together.

## The rules the kit applies (and why)
- **Public-domain shelf only.** The search (`kit/internetarchive-pd.yml`) only looks at the Internet Archive's Feature Films collection, and only at items marked public domain. A plain Archive search for *Night of the Living Dead* also returns the copyrighted 1990 remake and TV broadcasts.
- **Years in every title,** so Radarr can tell a 1968 original from a remake. Radarr also leaves the year out of its search, because many Archive titles don't include one.
- **One copy per film.** Some Archive uploads hold the same film in 28 formats (62 GB). `kit/keep-one-video.py` keeps the best playable file and renames it from the Archive's records, so Radarr recognises it.
- **Originals only.** Colorized versions are rejected. Archive files carry no quality labels, so Radarr's "Unknown" quality is allowed, with its size limit keeping giant uploads out.
- **Jellyfin updates instantly,** because Radarr tells it about each new film.
- **Small footprint:** only Jellyfin is reachable from your home network, and uploads are capped at 500 KB/s.

## Everyday
- Movies: `media/movies`. Downloads in progress: `media/downloads`.
- Stop: `stop`. Start again: `start`. Settings and your library are kept.
- Can't find a recent movie? That's by design: the kit only searches public-domain films.

## Troubleshooting
- **"Docker Desktop isn't running":** open Docker Desktop and wait until it says "Engine running".
- **Docker Desktop says "Virtualization support not detected" (Windows):** install WSL first (see Download above), restart, and open Docker Desktop again.
- **Port 8096 or 7878 is already in use:** another app is using it. Stop that app, or change the left-hand number under `ports:` in `docker-compose.yml`.
- **The TV can't connect:** use the address `start` showed you, on the same Wi-Fi. On Windows, allow Docker through the firewall if asked.
- **Setup hit a problem:** `start` prints the reason. Running `start` again is safe.

## Is this legal?
The kit only downloads films the Internet Archive marks public domain in its Feature Films collection. Public domain rules depend on your country; these films are public domain in the US. Downloading movies you don't have the rights to is illegal in most places. This kit isn't built for that and won't help with it.

## License
MIT (see [LICENSE](LICENSE)), except `kit/internetarchive-pd.yml`. That file is adapted from [Jackett](https://github.com/Jackett/Jackett)'s Internet Archive definition and, like the original, is under the GNU GPL v2.0 (see [LICENSES/GPL-2.0.txt](LICENSES/GPL-2.0.txt)). Jellyfin, Radarr, qBittorrent and Jackett are separate projects with their own licenses. The kit doesn't include them; it runs Jellyfin's official image and [LinuxServer.io](https://www.linuxserver.io)'s images of the other three.
