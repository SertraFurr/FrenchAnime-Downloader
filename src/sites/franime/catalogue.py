"""FRAnime: the whole catalogue (cached for a few minutes)."""
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

_FRANIME_CACHE = {"time": 0.0, "data": []}

_FRANIME_CACHE_SECONDS = 600

def _fetch_franime_catalogue(headers=None):
    # The whole catalogue is several MB and a search asks for it once per
    # keyword (and the season/episode steps again), so keep it for a few minutes.
    if _FRANIME_CACHE["data"] and time.time() - _FRANIME_CACHE["time"] < _FRANIME_CACHE_SECONDS:
        return _FRANIME_CACHE["data"]

    req_headers = {"User-Agent": "Mozilla/5.0"}
    if headers and "User-Agent" in headers:
        req_headers["User-Agent"] = headers["User-Agent"]
    try:
        r = requests.get(
            "https://api.franime.fr/api/animes",
            headers=req_headers,
            timeout=60,
        )
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(e)
        return []

    _FRANIME_CACHE["time"] = time.time()
    _FRANIME_CACHE["data"] = data
    return data

def texte(a):
    parts = [a.get("title"), a.get("titleO")] + list((a.get("titles") or {}).values())
    return " ".join(p for p in parts if isinstance(p, str)).lower()
