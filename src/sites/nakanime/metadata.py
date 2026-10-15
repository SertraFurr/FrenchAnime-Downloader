"""Nakanime: anime title, alternate titles, season number."""
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
from src.sites.nakanime.crypto import NAKANIME_DOMAIN

def _fetch_nakanime_alt_titles(base_url, headers=None):
    match = re.search(r'(https?://[^/]+/anime/\d+/[^/]+)', base_url)
    root_url = match.group(1) if match else base_url

    request_headers = dict(headers) if headers else {"User-Agent": "Mozilla/5.0"}
    cookies = None
    stored = get_domain_cookies(NAKANIME_DOMAIN)
    if stored:
        cf_clearance, stored_headers = stored
        request_headers["User-Agent"] = stored_headers["User-Agent"]
        # caller's headers may carry a Cookie for a different domain (e.g.
        # anime-sama.to's cf_clearance) - requests leaves an explicit Cookie
        # header untouched even when cookies= is passed, so the stale cookie
        # would silently win and nakanime.tv would 403 again.
        request_headers.pop("Cookie", None)
        request_headers.pop("cookie", None)
        cookies = {"cf_clearance": cf_clearance}

    try:
        response = requests.get(root_url, headers=request_headers, cookies=cookies, timeout=10)
        response.raise_for_status()
        html = response.text
    except requests.RequestException as e:
        print_status(f"Could not fetch alternate titles: {str(e)}", "warning")
        return []

    for ld_match in re.finditer(r'<script type=["\']application/ld\+json["\']>(.*?)</script>', html, re.DOTALL):
        try:
            data = json.loads(ld_match.group(1))
        except json.JSONDecodeError:
            continue

        if data.get('@type') != 'TVSeries':
            continue

        names = []
        for key in ("name", "alternateName"):
            value = data.get(key)
            if value and value.strip() and value.strip() not in names:
                names.append(value.strip())
        return names

    return []

def anime_name(base_url):
    unquoted = urllib.parse.unquote(base_url)
    nakanime_match = re.search(r'/anime/\d+/([^/&#?]+)', unquoted)
    if nakanime_match and nakanime_match.group(1) not in ['season', 'episode']:
        return nakanime_match.group(1)

    nakanime_id_match = re.search(r'/anime/(\d+)', unquoted)
    if nakanime_id_match:
        anime_id = nakanime_id_match.group(1)
        try:
            url = f"https://nakanime.tv/anime/{anime_id}/season/1/episode/1"
            req_headers = {"User-Agent": "Mozilla/5.0"}
            cookies = None
            stored = get_domain_cookies(NAKANIME_DOMAIN)
            if stored:
                cf_clearance, stored_headers = stored
                req_headers["User-Agent"] = stored_headers["User-Agent"]
                cookies = {"cf_clearance": cf_clearance}
            res = requests.get(url, headers=req_headers, cookies=cookies, timeout=5)
            scripts = re.findall(r'<script[^>]*>(.*?)</script>', res.text, re.DOTALL)
            for s in scripts:
                if 'title' in s and 'animeId' in s:
                    data = json.loads(s.strip())
                    title = data.get('title')
                    if title:
                        return title
        except Exception:
            pass
        return f"nakanime-{anime_id}"
    return "episode"

def alt_titles(base_url, headers=None):
    return _fetch_nakanime_alt_titles(base_url, headers=headers)

def season_info(base_url):
    m_season = re.search(r'/season/(\d+)', base_url)
    return f"saison{m_season.group(1)}" if m_season else "saison1"
