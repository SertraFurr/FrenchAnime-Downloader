"""french-manga: anime title, alternate titles, season number."""
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

def _frenchmanga_anime_name(base_url):
    """french-manga: the title is in the page's data-title attribute (the URL only has the
    accent-less name, "dtective-conan-..."). "- Saison N ..." is removed: the season number
    is given separately."""
    import html as _html
    try:
        res = _http.get(base_url, timeout=10)
        m = re.search(r'data-title="([^"]+)"', res.text)
        if m:
            titre = _html.unescape(m.group(1)).strip()
            titre = re.sub(r"\s*[-:]\s*Saison\s*\d+.*$", "", titre, flags=re.I).strip()
            if titre:
                return titre
    except requests.RequestException:
        pass
    # fallback: the name from the URL (without accents, but better than "episode")
    slug = urllib.parse.urlparse(base_url).path.rsplit("/", 1)[-1]
    slug = re.sub(r"^\d+-", "", slug)
    slug = re.sub(r"\.html$", "", slug)
    slug = re.sub(r"-saison-\d+(-\d{4})?$", "", slug)
    return slug.replace("-", " ").strip() or "episode"

def _fetch_frenchmanga_alt_titles(base_url, headers=None):
    """french-manga : l'API des episodes renvoie "alt_titles" {"jp": "A~B", "us": "C~D"}."""
    from urllib.parse import urlparse
    m = re.search(r"/(\d+)-", urlparse(base_url).path)
    if not m:
        return []
    parsed = urlparse(base_url)
    site = f"{parsed.scheme or 'https'}://{parsed.netloc}"
    try:
        r = _http.get(f"{site}/engine/ajax/manga_episodes_api.php", params={"id": m.group(1)},
                      timeout=10).json()
    except (requests.RequestException, ValueError):
        return []
    alt = r.get("alt_titles") if isinstance(r, dict) else None
    if not isinstance(alt, dict):
        return []
    names = []
    for value in alt.values():
        for nom in str(value).split("~"):
            nom = nom.strip()
            if nom and nom not in names:
                names.append(nom)
    # only titles in Latin letters help the TVDB/IMDb identification
    return [n for n in names if n.isascii()][:8]

def anime_name(base_url):
    return _frenchmanga_anime_name(base_url)

def alt_titles(base_url, headers=None):
    return _fetch_frenchmanga_alt_titles(base_url, headers=headers)

def season_info(base_url):
    # the season number is in the URL (".../1498700-one-piece-saison-23-1999.html");
    # a film or a special has none: season 1
    m_season = re.search(r'-saison-(\d+)', base_url, re.I)
    return f"saison{m_season.group(1) if m_season else 1}"
