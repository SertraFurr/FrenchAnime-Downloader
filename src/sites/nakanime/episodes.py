"""Nakanime: the player links of every episode."""
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
from src.sites.nakanime.crypto import NAKANIME_DOMAIN, derive_nakanime_key, decode_nakanime_response

def _get_nakanime_session_and_headers(headers=None):
    req_headers = {"User-Agent": "Mozilla/5.0"}
    if headers and "User-Agent" in headers:
        req_headers["User-Agent"] = headers["User-Agent"]

    session = requests.Session()

    # nakanime.tv started sitting behind a Cloudflare challenge that a plain
    # requests session can't solve - if the user has gone through the manual
    # cf_clearance setup (main.py prompts for this once per Cloudflare
    # expiry), reuse it here automatically. The cookie is only valid for the
    # exact User-Agent it was solved with, so that takes priority over
    # whatever caller passed in - a mismatched UA would just fail again.
    stored = get_domain_cookies(NAKANIME_DOMAIN)
    if stored:
        cf_clearance, stored_headers = stored
        req_headers["User-Agent"] = stored_headers["User-Agent"]
        session.cookies.set("cf_clearance", cf_clearance, domain=NAKANIME_DOMAIN)

    session.headers.update(req_headers)
    return session, req_headers

def _get_nakanime_episode_numbers(session, anime_id, target_season):
    """Only the list of existing episode numbers (1-2 requests, cheap) - kept
    apart from the per-episode sources fetch (the real cost)."""
    url_page = f"https://nakanime.tv/anime/{anime_id}/season/{target_season}/episode/1"
    res_page = session.get(url_page, timeout=10)

    ep_numbers = []
    scripts = re.findall(r'<script[^>]*>(.*?)</script>', res_page.text, re.DOTALL)
    for s in scripts:
        if 'animeId' in s and 'seasons' in s:
            try:
                data = json.loads(s.strip())
                for season in data.get('seasons', []):
                    if season.get('number', 1) == target_season:
                        eps = season.get('episodes', [])
                        ep_numbers = [e.get('number') for e in eps if e.get('number') is not None]
                        break
                break
            except Exception:
                pass

    if not ep_numbers:
        path_eps = f"/api/anime/{anime_id}/episodes"
        res = session.get(f"https://nakanime.tv{path_eps}", timeout=15)
        res.raise_for_status()
        decrypted = decode_nakanime_response(res.content, path_eps)
        data = json.loads(decrypted.decode('utf-8'))
        all_episodes = data.get('data', [])
        for ep in all_episodes:
            s_num = ep.get('seasonNumber')
            if s_num is None:
                s_num = 1
            if int(s_num) == target_season:
                ep_numbers.append(ep.get('number', 1))
        ep_numbers = sorted(list(set(ep_numbers)))

    return ep_numbers

NAKANIME_SOURCES_PATH = "/api/sources/anime"

def _fetch_nakanime_sources(session, anime_id, target_season, ep_num):
    """Sources of a Nakanime episode (list of host/language/url dicts), []
    if the episode exists but is not out yet, None if the request failed.
    Honours the site's Retry-After on a 429."""
    ep_page_url = f"https://nakanime.tv/anime/{anime_id}/season/{target_season}/episode/{ep_num}"
    url_src = f"https://nakanime.tv{NAKANIME_SOURCES_PATH}"

    for attempt in range(2):
        try:
            r_page = session.get(ep_page_url, timeout=10)
            if r_page.status_code == 429:
                wait_s = int(r_page.headers.get("Retry-After", 30)) + 1
                print_status(f"Rate-limited by Nakanime, waiting {wait_s}s before resuming...", "warning")
                time.sleep(wait_s)
                continue

            m_ep_id = re.search(r'data-episode-id=["\'](\d+)["\']', r_page.text)
            if not m_ep_id:
                raise ValueError("episode id not found")
            ep_id = int(m_ep_id.group(1))

            payload = {"anime_id": anime_id, "episode_id": ep_id, "turnstile_token": ""}
            r_src = session.post(url_src, headers={"Content-Type": "application/json"}, json=payload, timeout=10)
            if r_src.status_code == 429:
                wait_s = int(r_src.headers.get("Retry-After", 30)) + 1
                print_status(f"Rate-limited by Nakanime, waiting {wait_s}s before resuming...", "warning")
                time.sleep(wait_s)
                continue
            if r_src.status_code != 200:
                raise ValueError(f"sources request failed with status {r_src.status_code}")

            dec_src = decode_nakanime_response(r_src.content, NAKANIME_SOURCES_PATH)
            return json.loads(dec_src.decode('utf-8'))
        except Exception:
            if attempt == 0:
                time.sleep(0.8)
            continue
    return None

def fetch_nakanime_available_count(base_url, headers=None):
    """Highest episode number that already has sources, found by binary
    search (about ten requests instead of 2 per episode). Episodes come out
    in order, so available = 1..K. None if no episode is available or the
    probe fails."""
    unquoted = urllib.parse.unquote(base_url)
    match_anime = re.search(r'/anime/(\d+)', unquoted)
    if not match_anime:
        return None
    anime_id = int(match_anime.group(1))
    match_season = re.search(r'/season/(\d+)', unquoted)
    target_season = int(match_season.group(1)) if match_season else 1

    try:
        session, _ = _get_nakanime_session_and_headers(headers)
        numbers = _get_nakanime_episode_numbers(session, anime_id, target_season)
        if not numbers:
            return None
        lo, hi, best = 0, len(numbers) - 1, None
        while lo <= hi:
            mid = (lo + hi) // 2
            sources = _fetch_nakanime_sources(session, anime_id, target_season, numbers[mid])
            if sources is None:
                return None
            if sources:
                best = numbers[mid]
                lo = mid + 1
            else:
                hi = mid - 1
        return best
    except Exception:
        return None

def fetch_nakanime_episode_count(base_url, headers=None):
    """Only the number of available episodes, without the expensive fetch
    (one source request per episode). Used to ask the user which episodes
    they want BEFORE paying for the full fetch."""
    unquoted = urllib.parse.unquote(base_url)
    match_anime = re.search(r'/anime/(\d+)', unquoted)
    if not match_anime:
        return None
    anime_id = int(match_anime.group(1))
    match_season = re.search(r'/season/(\d+)', unquoted)
    target_season = int(match_season.group(1)) if match_season else 1

    try:
        session, _ = _get_nakanime_session_and_headers(headers)
        ep_numbers = _get_nakanime_episode_numbers(session, anime_id, target_season)
        return max(ep_numbers) if ep_numbers else None
    except Exception:
        return None

def fetch_nakanime_episodes(base_url, headers=None, wanted_episodes=None):
    unquoted = urllib.parse.unquote(base_url)
    match_anime = re.search(r'/anime/(\d+)', unquoted)
    if not match_anime:
        print_status("Could not determine Nakanime anime ID", "error")
        return None
    anime_id = int(match_anime.group(1))

    match_season = re.search(r'/season/(\d+)', unquoted)
    target_season = int(match_season.group(1)) if match_season else 1

    print_status(f"Fetching Nakanime player sources for Season {target_season}...", "loading")
    try:
        # One session for every request to nakanime.tv - reuses the TCP/TLS
        # connection (keep-alive) instead of opening one per request, which
        # speeds up a long series of sequential requests without changing the
        # rate/volume the server sees.
        session, req_headers = _get_nakanime_session_and_headers(headers)

        all_ep_numbers = _get_nakanime_episode_numbers(session, anime_id, target_season)
        if not all_ep_numbers:
            print_status(f"No episodes found for Season {target_season}", "error")
            return None

        # If the caller already knows which episodes it wants (chosen before
        # this fetch), only those pay the cost (and the rate limit) - the rest
        # keeps a None slot in the final list, aligned on the site's real
        # total number of episodes.
        if wanted_episodes:
            ep_numbers = [n for n in all_ep_numbers if n in wanted_episodes]
            if not ep_numbers:
                ep_numbers = all_ep_numbers
        else:
            ep_numbers = all_ep_numbers

        # Index by real episode number (not by arrival order) so the position in
        # the final list stays aligned on ep_num - 1 even if an episode fails
        # to fetch (otherwise every following episode would silently shift by
        # one slot).
        player_episodes_by_num = {}

        # Sending ~700 sequential requests without a pause triggers server-side
        # rate limiting, especially near the end of a long season - hence a
        # small delay between episodes and a retry before giving up on one.
        # Parallelism (several requests at once) was tried and makes things
        # worse: the server rate-limits harder with no real speed gain.
        #
        # The measured bottleneck: nakanime.tv lets ~60-100 quick requests
        # through, then answers 429 (Too Many Requests) with a Retry-After
        # header (e.g. 29s) for ALL the remaining episodes. Without detecting
        # it, every following episode "fails" in 0.1s then waits a far too
        # short backoff before failing again - hundreds of quick failures that
        # add up to minutes for nothing. Retry-After is now honoured once, as
        # soon as it is seen, instead of being retried in a loop too early.
        print_status(f"Fetching sources for {len(ep_numbers)} episodes...", "loading")
        for ep_num in ep_numbers:
            sources = _fetch_nakanime_sources(session, anime_id, target_season, ep_num)

            if sources:
                seen_counts = {}
                for item in sources:
                    host = item.get('host', 'unknown').capitalize()
                    lang = item.get('language', 'UNKNOWN')
                    base_key = f"{host} ({lang})"
                    seen_counts[base_key] = seen_counts.get(base_key, 0) + 1
                    cnt = seen_counts[base_key]
                    player_key = f"{host} {cnt} ({lang})" if cnt > 1 else base_key

                    player_episodes_by_num.setdefault(player_key, {})[ep_num] = item.get('url')

        if player_episodes_by_num:
            # Always sized on the season's real total (not just the requested
            # subset) so indexes stay consistent with what the rest of the
            # program (episode/player selection) already expects.
            max_ep_num = max(all_ep_numbers)
            player_episodes = {}
            for player_key, urls_by_num in player_episodes_by_num.items():
                # list of size max_ep_num, index i is episode i+1
                # (None for an episode that failed to fetch or lacks this player)
                episode_list = [urls_by_num.get(n) for n in range(1, max_ep_num + 1)]
                player_episodes[player_key] = episode_list
            print_status(f"Found {len(player_episodes)} player sources across VF & VOSTFR!", "success")
            return player_episodes
        else:
            print_status("No working video players found for this season", "error")
            return None
            
    except Exception as e:
        print_status(f"Failed to fetch Nakanime episodes: {str(e)}", "error")
        return None
