#!/usr/bin/env python3
"""Digest Movie Night Kit setup.

prep     runs before qBittorrent and Jackett start: gives qBittorrent an internal password (you never need it)
         and copies in the kit's one-copy helper and its public-domain search file.
wire     runs after everything starts: connects the apps to each other and applies the kit's rules.
         Safe to run again: it only adds what's missing and re-applies the rules.
tonight  the nightly shopping trip (tonight.bat / tonight.sh run it): checks the Movie Night list if it's switched
         on, then searches for every movie on the wishlist that isn't downloaded yet.
"""
import base64, hashlib, http.cookiejar, json, os, re, secrets, shutil, sys, time
import urllib.error, urllib.parse, urllib.request

KIT = "/kit"
QBT_CONF = "/qbt-config/qBittorrent/qBittorrent.conf"
QBT_SECRET = "/qbt-config/kit-password.txt"
JACKETT_DEF = "/jackett-config/cardigann/definitions/internetarchive-pd.yml"
JF_AUTH = 'MediaBrowser Client="Movie Night Kit", Device="setup", DeviceId="movie-night-kit-setup", Version="1.0"'
JF_KEY_NAME = "Radarr (Movie Night Kit)"
INDEXER_NAME = "Internet Archive (public domain)"
LIST_NAME = "Digest Movie Night list"
LIST_URL = "https://raw.githubusercontent.com/fighterz8/digest-movie-night-kit/main/movies.json"


def say(msg):
    print(msg, flush=True)


class Http:
    def __init__(self, base, headers=None):
        self.base, self.headers = base, headers or {}
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def call(self, path, method=None, body=None, form=None, timeout=180):
        data, headers = None, dict(self.headers)
        if body is not None:
            data, headers["Content-Type"] = json.dumps(body).encode(), "application/json"
        elif form is not None:
            data = urllib.parse.urlencode(form).encode()
        req = urllib.request.Request(self.base + path, data=data, headers=headers,
                                     method=method or ("POST" if data is not None else "GET"))
        with self.opener.open(req, timeout=timeout) as r:
            text = r.read().decode()
        try:
            return json.loads(text)
        except ValueError:
            return text


def wait_for(name, check, minutes=10):
    deadline = time.time() + minutes * 60
    while True:
        try:
            return check()
        except (urllib.error.URLError, ConnectionError, OSError, KeyError, AttributeError) as e:
            if time.time() > deadline:
                raise SystemExit(f"{name} didn't come up within {minutes} minutes ({e})")
            time.sleep(3)


def fill(schema, **values):
    for f in schema["fields"]:
        if f["name"] in values:
            f["value"] = values[f["name"]]
    return schema


# ---------------------------------------------------------------- prep

def prep():
    os.makedirs(os.path.dirname(QBT_CONF), exist_ok=True)
    if not os.path.exists(QBT_CONF):
        password = secrets.token_urlsafe(18)
        salt = os.urandom(16)
        key = hashlib.pbkdf2_hmac("sha512", password.encode(), salt, 100000, 64)
        with open(QBT_CONF, "w") as f:
            f.write("[LegalNotice]\nAccepted=true\n\n")  # otherwise qBittorrent waits for someone to accept it
            f.write("[Preferences]\n")
            f.write("WebUI\\Username=admin\n")
            f.write('WebUI\\Password_PBKDF2="@ByteArray(%s:%s)"\n'
                    % (base64.b64encode(salt).decode(), base64.b64encode(key).decode()))
        with open(QBT_SECRET, "w") as f:
            f.write(password)
        os.chmod(QBT_SECRET, 0o600)
        say("qBittorrent: internal password set")
    shutil.copy(f"{KIT}/keep-one-video.py", "/qbt-config/keep-one-video.py")
    os.makedirs(os.path.dirname(JACKETT_DEF), exist_ok=True)
    shutil.copy(f"{KIT}/internetarchive-pd.yml", JACKETT_DEF)
    say("prep: one-copy helper and public-domain search file copied in")


# ---------------------------------------------------------------- wire

def settings():
    user = (os.environ.get("USERNAME") or "admin").strip().strip('"')
    password = (os.environ.get("PASSWORD") or "").strip().strip('"')
    if not password or password == "change-me":
        raise SystemExit("Pick a password in settings.txt first, then run start again.")
    return user, password


def list_setting():
    """MOVIE_LIST=on in settings.txt follows the kit's list of public-domain films (MOVIE_LIST_URL points at a
    different list, for testing or a fork)."""
    on = (os.environ.get("MOVIE_LIST") or "off").strip().strip('"').lower() in ("on", "yes", "true", "1")
    return on, (os.environ.get("MOVIE_LIST_URL") or LIST_URL).strip().strip('"')


def radarr_api(minutes=10):
    def ready():
        key = re.search(r"<ApiKey>(\w+)</ApiKey>", open("/radarr-config/config.xml").read()).group(1)
        Http("http://radarr:7878/api/v3", {"X-Api-Key": key}).call("/system/status")
        return key
    return Http("http://radarr:7878/api/v3", {"X-Api-Key": wait_for("Radarr", ready, minutes)})


def wire_qbittorrent():
    secret = open(QBT_SECRET).read().strip()
    qbt = Http("http://qbittorrent:8080/api/v2", {"Referer": "http://qbittorrent:8080"})

    def login():
        if "Fails" in str(qbt.call("/auth/login", form={"username": "admin", "password": secret})):
            raise SystemExit("qBittorrent didn't accept the kit's internal password")
    wait_for("qBittorrent", login)
    prefs = {"save_path": "/data/downloads", "bypass_local_auth": True, "up_limit": 500 * 1024,
             "autorun_on_torrent_added_enabled": True,
             "autorun_on_torrent_added_program": 'python3 /config/keep-one-video.py "%I"'}
    qbt.call("/app/setPreferences", form={"json": json.dumps(prefs)})
    say("qBittorrent: downloads go to media/downloads, one-copy helper on, uploads capped at 500 KB/s")
    return secret


def wire_jackett():
    jk = Http("http://jackett:9117")
    wait_for("Jackett", lambda: jk.call("/UI/Dashboard"))
    key = wait_for("Jackett's settings", lambda: json.load(open("/jackett-config/Jackett/ServerConfig.json"))["APIKey"])
    if not any(i.get("id") == "internetarchive-pd" for i in jk.call("/api/v2.0/indexers?configured=true")):
        cfg = jk.call("/api/v2.0/indexers/internetarchive-pd/config")
        jk.call("/api/v2.0/indexers/internetarchive-pd/config", body=cfg)
        say("Jackett: public-domain Internet Archive search added")
    return key


def wire_jellyfin(user, password):
    jf = Http("http://jellyfin:8096", {"Authorization": JF_AUTH})
    info = wait_for("Jellyfin", lambda: jf.call("/System/Info/Public")["Version"] and jf.call("/System/Info/Public"))
    if not info.get("StartupWizardCompleted"):
        jf.call("/Startup/Configuration", body={"UICulture": "en-US", "MetadataCountryCode": "US",
                                                "PreferredMetadataLanguage": "en"})
        jf.call("/Startup/User")
        jf.call("/Startup/User", body={"Name": user, "Password": password})
        jf.call("/Startup/RemoteAccess", body={"EnableRemoteAccess": True, "EnableAutomaticPortMapping": False})
        jf.call("/Startup/Complete", method="POST")
        say(f"Jellyfin: first-run setup done (user '{user}')")
    try:
        auth = jf.call("/Users/AuthenticateByName", body={"Username": user, "Pw": password})
    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise SystemExit("Jellyfin didn't accept the name and password in settings.txt. If you changed them in "
                             "Jellyfin, put the same ones in settings.txt.")
        raise
    ja = Http("http://jellyfin:8096", {"Authorization": JF_AUTH + f', Token="{auth["AccessToken"]}"'})
    if not any(lib["Name"] == "Movies" for lib in ja.call("/Library/VirtualFolders")):
        ja.call("/Library/VirtualFolders?name=Movies&collectionType=movies&refreshLibrary=false",
                body={"LibraryOptions": {"EnableRealtimeMonitor": True, "PathInfos": [{"Path": "/data/movies"}]}})
        say("Jellyfin: Movies library added")
    ja.call("/Library/Refresh", method="POST")  # a full scan also starts Jellyfin watching the folder
    keys = ja.call("/Auth/Keys")["Items"]
    if not any(k.get("AppName") == JF_KEY_NAME for k in keys):
        ja.call("/Auth/Keys?app=" + urllib.parse.quote(JF_KEY_NAME), method="POST")
        keys = ja.call("/Auth/Keys")["Items"]
    config = ja.call("/System/Configuration")
    if not config.get("ServerName"):  # unnamed, TV apps would show the container's random ID
        config["ServerName"] = "Movie Night"
        ja.call("/System/Configuration", body=config)
        say("Jellyfin: server named 'Movie Night'")
    return next(k["AccessToken"] for k in keys if k.get("AppName") == JF_KEY_NAME)


def wire_radarr(user, password, qbt_secret, jackett_key, jellyfin_key):
    r = radarr_api()

    host = r.call("/config/host")
    if host.get("authenticationMethod", "none") == "none":
        # Radarr 6 wants a list of allowed host names when sign-in is skipped for this computer, and only starts
        # enforcing it after a restart. "radarr" is how this setup step reaches it.
        host.update(authenticationMethod="forms", authenticationRequired="disabledForLocalAddresses",
                    allowedHosts="localhost,127.0.0.1,radarr",
                    username=user, password=password, passwordConfirmation=password)
        r.call(f"/config/host/{host['id']}", method="PUT", body=host)
        r.call("/system/restart", method="POST")
        time.sleep(5)
        wait_for("Radarr (after restart)", lambda: r.call("/system/status"))
        say("Radarr: sign-in set (none needed on this computer; other host names are refused)")

    if not any(f["path"] == "/data/movies" for f in r.call("/rootfolder")):
        r.call("/rootfolder", body={"path": "/data/movies"})

    if not r.call("/downloadclient"):
        s = next(x for x in r.call("/downloadclient/schema") if x["implementation"] == "QBittorrent")
        fill(s, host="qbittorrent", port=8080, username="admin", password=qbt_secret, movieCategory="radarr")
        s.update(name="qBittorrent", enable=True, priority=1)
        r.call("/downloadclient", body=s)  # Radarr tests the connection before saving

    if not any(i["name"] == INDEXER_NAME for i in r.call("/indexer")):
        s = next(x for x in r.call("/indexer/schema") if x["implementation"] == "Torznab")
        fill(s, baseUrl="http://jackett:9117/api/v2.0/indexers/internetarchive-pd/results/torznab/", apiPath="/api",
             apiKey=jackett_key, categories=[2000], minimumSeeders=1, removeYear=True)
        s.update(name=INDEXER_NAME, enableRss=True, enableAutomaticSearch=True, enableInteractiveSearch=True,
                 priority=25)
        r.call("/indexer", body=s)  # Radarr runs a test search before saving

    # Originals only: colorized versions and commercial disc rips (which can carry a restoration or a newer score
    # that is still copyrighted) are rejected.
    rules = {"Colorized": r"\bcolou?ri[sz]ed\b",
             "Commercial disc rip": r"\b(blu[ ._-]?ray|remux|bdrip|brrip|web[ ._-]?dl|webrip)\b"}
    formats = {c["name"]: c for c in r.call("/customformat")}
    for name, regex in rules.items():
        if name not in formats:
            formats[name] = r.call("/customformat", body={
                "name": name, "includeCustomFormatWhenRenaming": False,
                "specifications": [{"name": name.lower() + " in the title", "implementation": "ReleaseTitleSpecification",
                                    "negate": False, "required": True, "fields": [{"name": "value", "value": regex}]}]})
    reject = {formats[name]["id"] for name in rules}
    for p in r.call("/qualityprofile"):
        if p["name"] != "Any":
            continue
        for item in p["items"]:
            if (item.get("quality") or {}).get("name") == "Unknown":
                item["allowed"] = True  # Archive uploads carry no quality labels
        for fi in p["formatItems"]:
            if fi["format"] in reject:
                fi["score"] = -10000
        r.call(f"/qualityprofile/{p['id']}", method="PUT", body=p)

    naming = r.call("/config/naming")
    naming.update(renameMovies=True, standardMovieFormat="{Movie Title} ({Release Year})")
    r.call(f"/config/naming/{naming['id']}", method="PUT", body=naming)

    if not any(n["implementation"] == "MediaBrowser" for n in r.call("/notification")):
        s = next(x for x in r.call("/notification/schema") if x["implementation"] == "MediaBrowser")
        fill(s, host="jellyfin", port=8096, useSsl=False, apiKey=jellyfin_key, notify=False, updateLibrary=True)
        s["name"] = "Jellyfin"
        for event in ("onDownload", "onUpgrade", "onRename", "onMovieDelete", "onMovieFileDelete"):
            if s.get("supports" + event[0].upper() + event[1:]):
                s[event] = True
        r.call("/notification", body=s)  # Radarr checks it can reach Jellyfin before saving
    say("Radarr: connected to qBittorrent, the public-domain search and Jellyfin; rules applied")
    wire_movie_list(r)


def wire_movie_list(r):
    """The list decides what, the schedule decides when: films on the list go on the wishlist, and they download
    when tonight runs (or when you click Search in Radarr)."""
    on, url = list_setting()
    existing = next((l for l in r.call("/importlist") if l["name"] == LIST_NAME), None)
    if not on:
        if existing and existing["enabled"]:
            existing.update(enabled=False, enableAuto=False)
            r.call(f"/importlist/{existing['id']}", method="PUT", body=existing)
            say("Radarr: Movie Night list switched off (the movies it added stay)")
        return
    profile = next(p["id"] for p in r.call("/qualityprofile") if p["name"] == "Any")
    s = existing or next(x for x in r.call("/importlist/schema") if x["implementation"] == "RadarrListImport")
    fill(s, url=url)
    s.update(name=LIST_NAME, enabled=True, enableAuto=True, searchOnAdd=False, monitor="movieOnly",
             rootFolderPath="/data/movies", qualityProfileId=profile, minimumAvailability="released")
    if existing:
        r.call(f"/importlist/{existing['id']}", method="PUT", body=s)
    else:
        r.call("/importlist", body=s)  # Radarr fetches the list before saving
    say("Radarr: following the Movie Night list (its films download when tonight runs)")


def run_command(r, name, minutes=10, **args):
    cmd = r.call("/command", body={"name": name, **args})
    deadline = time.time() + minutes * 60
    while time.time() < deadline:
        state = r.call(f"/command/{cmd['id']}")
        if state.get("status") in ("completed", "failed", "aborted", "cancelled", "orphaned"):
            return state
        time.sleep(2)
    return {"status": "still running"}


def tonight():
    try:
        r = radarr_api(minutes=2)
    except SystemExit:
        raise SystemExit("Radarr isn't answering. Is the kit running? Double-click start, then try again.")
    on, _ = list_setting()
    movie_list = next((l for l in r.call("/importlist") if l["name"] == LIST_NAME and l["enabled"]), None)
    if on and movie_list:
        # Naming the list makes Radarr read it now; a plain sync skips lists read in the last 12 hours.
        done = run_command(r, "ImportListSync", definitionId=movie_list["id"])
        say(f"Checked the Movie Night list: {done.get('message') or done.get('status')}")
    elif on:
        say("MOVIE_LIST is on, but Radarr isn't following the list yet: run start once to set it up.")
    missing = [m for m in r.call("/movie") if m.get("monitored") and not m.get("hasFile") and m.get("isAvailable")]
    if not missing:
        say("Nothing on your wishlist is missing, so there's nothing to download tonight.")
        return
    names = [f"{m['title']} ({m['year']})" for m in missing]
    say(f"Tonight's shopping list ({len(names)}): " + ", ".join(names[:15]) + (", ..." if len(names) > 15 else ""))
    r.call("/command", body={"name": "MissingMoviesSearch"})
    say("The robot is searching the Archive's public-domain shelf. Downloads appear under Activity in Radarr.")


def wire():
    user, password = settings()
    qbt_secret = wire_qbittorrent()
    jackett_key = wire_jackett()
    jellyfin_key = wire_jellyfin(user, password)
    wire_radarr(user, password, qbt_secret, jackett_key, jellyfin_key)
    say("READY")


if __name__ == "__main__":
    try:
        {"prep": prep, "wire": wire, "tonight": tonight}[sys.argv[1]]()
    except urllib.error.HTTPError as e:
        raise SystemExit(f"{e.url} answered {e.code}: {e.read().decode(errors='replace')[:400]}")
