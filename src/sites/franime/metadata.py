"""FRAnime: anime title, alternate titles, season number."""
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
from src.sites.franime.seasons import extract_franime_id, extract_franime_season, find_franime_anime

def _fetch_franime_alt_titles(base_url, headers=None):
    from src.sites.franime.seasons import extract_franime_id, find_franime_anime
    try:
        anime = find_franime_anime(extract_franime_id(base_url), headers)
    except (KeyError, ValueError):
        return []
    if not anime:
        return []
    names = []
    for value in [anime.get("title"), anime.get("titleO")] + list((anime.get("titles") or {}).values()):
        if isinstance(value, str) and value.strip() and value.strip() not in names:
            names.append(value.strip())
    # the catalogue lists the title in dozens of languages; only latin ones help
    # the TVDB/IMDb lookup, and a handful is plenty
    return [n for n in names if n.isascii()][:8]

def anime_name(base_url):
    # franime URLs carry no title (only ?anime_id=); it lives in the catalogue
    try:
        anime = find_franime_anime(extract_franime_id(base_url))
    except (KeyError, ValueError):
        anime = None
    if anime:
        return anime.get("title") or anime.get("titleO") or "episode"
    return "episode"

def alt_titles(base_url, headers=None):
    return _fetch_franime_alt_titles(base_url, headers=headers)

def season_info(base_url):
    return f"saison{extract_franime_season(base_url)}"
