"""Nakanime: the seasons of an anime."""
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

def expand_nakanime_url(url, headers=None):
    unquoted = urllib.parse.unquote(url)
    match = re.search(r'/anime/(\d+)', unquoted)
    if not match:
        return []
    anime_id = match.group(1)
    
    req_headers = {"User-Agent": "Mozilla/5.0"}
    if headers and "User-Agent" in headers:
        req_headers["User-Agent"] = headers["User-Agent"]
    # a caller-supplied headers dict (e.g. fallback.py's) may carry a Cookie
    # for a different domain - an explicit Cookie header beats cookies= in
    # requests, so the stale cookie would silently win over the one we set below.
    req_headers.pop("Cookie", None)
    req_headers.pop("cookie", None)

    nk_cookies = None
    stored = get_domain_cookies(NAKANIME_DOMAIN)
    if stored:
        cf_clearance, stored_headers = stored
        req_headers["User-Agent"] = stored_headers["User-Agent"]
        nk_cookies = {"cf_clearance": cf_clearance}

    seasons = set()

    try:
        url_page = f"https://nakanime.tv/anime/{anime_id}/season/1/episode/1"
        res_page = requests.get(url_page, headers=req_headers, cookies=nk_cookies, timeout=10)
        scripts = re.findall(r'<script[^>]*>(.*?)</script>', res_page.text, re.DOTALL)
        for s in scripts:
            if 'animeId' in s and 'seasons' in s:
                try:
                    data = json.loads(s.strip())
                    for season in data.get('seasons', []):
                        s_num = season.get('number', 1)
                        if s_num is not None:
                            seasons.add(int(s_num))
                    break
                except Exception:
                    pass
    except Exception:
        pass

    if not seasons:
        try:
            path = f"/api/anime/{anime_id}/episodes"
            api_url = f"https://nakanime.tv{path}"
            res = requests.get(api_url, headers=req_headers, cookies=nk_cookies, timeout=10)
            res.raise_for_status()
            decrypted = decode_nakanime_response(res.content, path)
            data = json.loads(decrypted.decode('utf-8'))
            episodes = data.get('data', [])
            for ep in episodes:
                s_num = ep.get('seasonNumber')
                if s_num is None:
                    s_num = 1
                seasons.add(int(s_num))
        except Exception:
            pass

    if not seasons:
        seasons.add(1)
        
    results = []
    for s_num in sorted(seasons):
        results.append({
            "name": f"Saison {s_num}",
            "url": f"https://nakanime.tv/anime/{anime_id}/season/{s_num}/episode/1"
        })
    return results
