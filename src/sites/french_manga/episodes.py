"""french-manga: the player links of every episode."""
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
from src.sites.french_manga import http as _http

def _frenchmanga_site(base_url):
    """https://<subdomain>.french-manga.net: the site changes subdomain (w16, w17...),
    so we reuse the one of the URL we received instead of hardcoding it."""
    parsed = urllib.parse.urlparse(base_url)
    return f"{parsed.scheme or 'https'}://{parsed.netloc or 'w16.french-manga.net'}"

def fetch_frenchmanga_episodes(base_url, headers=None, wanted_episodes=None):
    match = re.search(r"/(\d+)-", base_url)
    if not match:
        print_status("Could not determine the french-manga anime ID", "error")
        return None
    news_id = match.group(1)

    print_status("Fetching french-manga player sources...", "loading")
    try:
        r = _http.get(
            f"{_frenchmanga_site(base_url)}/engine/ajax/manga_episodes_api.php",
            params={"id": news_id},
            timeout=30,
        ).json()
    except (requests.RequestException, ValueError) as e:
        print_status(f"Failed to fetch french-manga episodes: {e}", "error")
        return None

    langues = ("vf", "vostfr")

    # season size: the highest episode number, all languages together
    numeros = [int(k) for langue in langues for k in (r.get(langue) or {}) if str(k).isdigit()]
    if not numeros:
        print_status("No episodes found for this season", "error")
        return None
    taille = max(numeros)

    episodes = {}
    for langue in langues:
        for numero, lecteurs in (r.get(langue) or {}).items():
            if not str(numero).isdigit():
                continue
            for nom, lien in (lecteurs or {}).items():
                if not lien:
                    continue
                cle = f"{nom.capitalize()} ({langue.upper()})"
                episodes.setdefault(cle, [None] * taille)[int(numero) - 1] = lien

    if not episodes:
        print_status("No working video players found for this season", "error")
        return None
    return episodes

def fetch_frenchmanga_episode_count(base_url, headers=None):
    match = re.search(r"/(\d+)-", base_url)
    if not match:
        return None
    try:
        r = _http.get(
            f"{_frenchmanga_site(base_url)}/engine/ajax/manga_episodes_api.php",
            params={"id": match.group(1)},
            timeout=30,
        ).json()
    except (requests.RequestException, ValueError):
        return None

    numeros = [int(k) for langue in ("vf", "vostfr") for k in (r.get(langue) or {}) if str(k).isdigit()]
    return max(numeros) if numeros else None
