"""french-manga: the seasons of an anime."""
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

def get_frenchmanga_seasons(title_base, base_site="https://w16.french-manga.net"):
    """The seasons the site knows for this anime name: [{"url", "season_number", "title"}, ...].
    Empty list if the site does not answer or the answer is not the expected one."""
    try:
        r = _http.get(
            f"{base_site}/engine/ajax/get_seasons.php",
            params={"title_base": title_base},
            timeout=30,
        )
        donnees = r.json()
    except (requests.RequestException, ValueError):
        return []

    if not isinstance(donnees, list):
        return []

    saisons = []
    for entree in donnees:
        if not isinstance(entree, dict) or not entree.get("full_url"):
            continue
        saisons.append({
            "url": entree["full_url"],
            "season_number": entree.get("season_number"),
            "title": entree.get("title") or "",
        })
    return saisons

def extract_frenchmanga_title_base(url):
    """The anime name the search slipped into the URL (?title_base=...)."""
    valeurs = parse_qs(urlparse(url).query).get("title_base")
    return valeurs[0] if valeurs else None

def expand_frenchmanga_url(url, headers=None):
    title_base = extract_frenchmanga_title_base(url)
    if not title_base:
        return []

    parsed = urlparse(url)
    base_site = f"{parsed.scheme}://{parsed.netloc}"

    saisons = get_frenchmanga_seasons(title_base, base_site)
    if not saisons and "'" in title_base:
        # the site does not find a title that contains an apostrophe: search with
        # the beginning of the title, then keep only the entry whose id is the
        # one of the URL we received.
        m_id = re.search(r"/(\d+)-", urlparse(url).path)
        saisons = get_frenchmanga_seasons(title_base.split("'")[0], base_site)
        if m_id:
            saisons = [s for s in saisons if f"/{m_id.group(1)}-" in "/" + s["url"]]

    resultat = []
    for saison in saisons:
        numero = saison["season_number"]
        # 999 = film or special: not a real season, keep its title
        if numero in (None, 999, "999"):
            nom = saison["title"].replace("\\'", "'") or "Film"
        else:
            nom = f"Saison {numero}"
        resultat.append({"name": nom, "url": urljoin(base_site + "/", saison["url"])})
    return resultat
