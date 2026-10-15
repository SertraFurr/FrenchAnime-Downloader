"""FRAnime: the seasons of an anime."""
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

def extract_franime_id(url):
    morceaux = urlparse(url)
    params2 = parse_qs(morceaux.query)
    return int(params2["anime_id"][0])

def extract_franime_season(url):
    morceaux = urlparse(url)
    params2 = parse_qs(morceaux.query)
    return params2.get("s", ["1"])[0]

def find_franime_anime(anime_id, headers=None):
    # One anime is ~6 KB from /anime-by-id/ (no cookie needed) where the full
    # catalogue is ~11 MB: ask for that, and only fall back to scanning the
    # catalogue if the answer is not the anime we asked for.
    req_headers = {"User-Agent": "Mozilla/5.0"}
    if headers and "User-Agent" in headers:
        req_headers["User-Agent"] = headers["User-Agent"]
    try:
        r = requests.get(f"https://api.franime.fr/api/anime-by-id/{anime_id}", headers=req_headers, timeout=20)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, dict) and data.get("id") == anime_id and "saisons" in data:
                return data
    except Exception:
        pass

    from src.sites.franime.catalogue import _fetch_franime_catalogue
    data = _fetch_franime_catalogue(headers)

    for a in data:
        if a["id"] == anime_id:
            return a
    return None

def extraire_numero(titre):
    liste = re.findall(r"\d+(?:\.\d+)?", titre)

    if not liste:
        return None
    return liste[-1]

def trouver_position_saison(anime, s):
    """franime's API wants the position (0, 1, ...) of the season in the list,
    while the URL carries its number (s=1, s=1.1)."""
    for i, saison in enumerate(anime["saisons"]):
        numero = extraire_numero(saison["title"])
        if numero == s:
            return i
    return None

def expand_franime_url(url, headers=None):
    saisons=[]
    anime_id = extract_franime_id(url)
    anime = find_franime_anime(anime_id, headers)

    if anime is None:
        return []

    for saison in anime["saisons"]:
        numero = extraire_numero(saison["title"])
        if numero is None:
            continue

        saisons.append({"name": f"Saison {numero}", "url": f"https://franime.fr/anime/test?s={numero}&anime_id={anime_id}"})

    return saisons
