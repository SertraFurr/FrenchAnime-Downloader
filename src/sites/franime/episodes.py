"""FRAnime: the player links of every episode."""
import re
import json
import time
import base64
import string
import requests
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse, parse_qs, urljoin, urlencode
from bs4 import BeautifulSoup
from src.var import get_domain, print_status
from src.utils.config.config import get_domain_cookies
from src.sites.franime.seasons import (
    extract_franime_id, extract_franime_season, find_franime_anime, trouver_position_saison,
)

FRANIME_DOMAIN = "franime.fr"

FRANIME_API = "https://api.franime.fr/api/anime"

FRANIME_API_HEADERS = {"Origin": "https://franime.fr", "Referer": "https://franime.fr/"}

# Any real episode works: only used to check that the cf_clearance cookie is still accepted.
FRANIME_TEST_URL = f"{FRANIME_API}/210/0/0/vo/0"

FRANIME_LANG_NAMES = {"vo": "VOSTFR", "vf": "VF"}

_PRINTABLE = set(string.printable.encode())

def decode_franime_watch_url(watch_url):
    """franime answers with a franime.fr/watch2/?a=...&b=... link whose 15 query
    parameters are decoys except one: base64 -> hex -> bytes XOR a one-byte key
    that is the real player URL. The key and the parameter vary, so try them all."""
    params = parse_qs(urlparse(watch_url).query)
    for values in params.values():
        try:
            text = base64.b64decode(values[0] + "=" * (-len(values[0]) % 4))
            raw = bytes.fromhex(text.decode())
        except Exception:
            continue
        for key in range(256):
            clear = bytes(byte ^ key for byte in raw)
            if clear.startswith(b"http") and all(c in _PRINTABLE for c in clear):
                return clear.decode()
    return None

def _franime_request_args():
    # The caller's headers are never reused: they may carry another site's
    # Cookie header, which would silently beat the cookies= argument.
    req_headers = {"User-Agent": "Mozilla/5.0", **FRANIME_API_HEADERS}
    cookies = None
    stored = get_domain_cookies(FRANIME_DOMAIN)
    if stored:
        cf_clearance, stored_headers = stored
        req_headers["User-Agent"] = stored_headers["User-Agent"]
        cookies = {"cf_clearance": cf_clearance}
    return req_headers, cookies

_FRANIME_MIN_GAP = 0.7           # seconds between two API calls (0.35s got us throttled after ~140 calls)

_franime_throttled = [False]     # set when franime starts serving decoy links

_franime_last_call = [0.0]

def _franime_get(url, req_headers, cookies):
    """One API call, paced, and patient with the rate limit: franime answers 429
    (Retry-After ~10s) after ~25 quick requests, and treating that like "no more
    players" silently dropped the last episodes of a selection."""
    r = None
    for _ in range(6):
        wait = _FRANIME_MIN_GAP - (time.time() - _franime_last_call[0])
        if wait > 0:
            time.sleep(wait)
        _franime_last_call[0] = time.time()
        try:
            r = requests.get(url, headers=req_headers, cookies=cookies, timeout=30)
        except requests.RequestException:
            return None
        if r.status_code != 429:
            return r
        try:
            delay = int(r.headers.get("Retry-After", 10))
        except ValueError:
            delay = 10
        time.sleep(min(delay, 30) + 1)
    return r

def get_franime_players(anime_id, season_index, episode_index, lang, expected=None):
    """Player URLs of one episode in one language, in the same order as the
    catalogue's `lecteurs` list (`expected` = its length, which saves the final
    404 request). The API answers 404 once there are no more."""
    req_headers, cookies = _franime_request_args()
    urls = []
    i = 0
    while i < (expected or 30):
        url = f"{FRANIME_API}/{anime_id}/{season_index}/{episode_index}/{lang}/{i}"
        r = _franime_get(url, req_headers, cookies)
        if r is None:
            break
        if r.status_code == 403:
            print_status("Franime refused the request (Cloudflare cookie missing or expired).", "error")
            break
        if r.status_code == 429:
            print_status(f"Franime rate limit still active - episode {episode_index + 1} ({lang}) is incomplete.", "warning")
            break
        if r.status_code != 200:
            break
        if not r.text.strip().startswith("https://franime.fr/watch2"):
            # Past some request volume the API keeps answering 200 but with a
            # random, unrelated Sibnet link instead of the real watch2 one.
            _franime_throttled[0] = True
            break
        player_url = decode_franime_watch_url(r.text)
        if player_url:
            urls.append(player_url)
        i += 1
    return urls

def build_franime_players(anime_id, season_index, episode_index, lang, expected=None):
    from src.utils.get.get_player_choice import _detect_host

    players = {}
    seen = {}
    for url in get_franime_players(anime_id, season_index, episode_index, lang, expected):
        host = _detect_host("", [url]).capitalize() or "Unknown"
        seen[host] = seen.get(host, 0) + 1
        key = host if seen[host] == 1 else f"{host} {seen[host]}"
        players[key] = url
    return players

def _franime_season_episodes(base_url, headers=None):
    """(anime_id, season position, episodes list) or None."""
    anime_id = extract_franime_id(base_url)
    anime = find_franime_anime(anime_id, headers)
    if anime is None:
        return None
    position = trouver_position_saison(anime, extract_franime_season(base_url))
    if position is None:
        return None
    return anime_id, position, anime["saisons"][position]["episodes"]

def fetch_franime_episode_count(base_url, headers=None):
    found = _franime_season_episodes(base_url, headers)
    return len(found[2]) if found else None

def fetch_franime_episodes(base_url, headers=None, wanted_episodes=None):
    found = _franime_season_episodes(base_url, headers)
    if found is None:
        print_status("Franime: anime or season not found.", "error")
        return None
    anime_id, position, episodes = found

    print_status("Fetching Franime player sources...", "loading")
    _franime_throttled[0] = False
    by_key = {}
    for number, ep in enumerate(episodes, 1):
        if _franime_throttled[0]:
            break
        if wanted_episodes and number not in wanted_episodes:
            continue
        for lang in ("vo", "vf"):
            if _franime_throttled[0]:
                break
            # the catalogue already says which languages exist for this episode
            if not ep["lang"][lang]["lecteurs"]:
                continue
            players = build_franime_players(anime_id, position, number - 1, lang, len(ep["lang"][lang]["lecteurs"]))
            for name, url in players.items():
                by_key.setdefault(f"{name} ({FRANIME_LANG_NAMES[lang]})", {})[number] = url

    if _franime_throttled[0]:
        print_status("Franime is throttling this connection (it answers fake links after too many requests). "
                     "Stopped to avoid wrong results - wait 10-15 minutes and retry, with fewer episodes if you can.", "error")
        return None
    if not by_key:
        print_status("No working video players found for this season", "error")
        return None
    # lists sized on the whole season so index i is always episode i+1
    result = {
        key: [by_number.get(n) for n in range(1, len(episodes) + 1)]
        for key, by_number in by_key.items()
    }
    print_status(f"Found {len(result)} player sources across VF & VOSTFR!", "success")
    return result
