"""french-manga: search."""
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
from src.sites._utils import dedupe as _dedupe
from src.sites.french_manga import http as _http

def _search_frenchmanga_one(query, headers=None):
    base_site = "https://w16.french-manga.net"
    try:
        r = _http.post(
            f"{base_site}/engine/ajax/search.php",
            data={"query": query},
            timeout=30,
        )
        r.raise_for_status()
    except requests.RequestException:
        return []

    resultats = []
    soup = BeautifulSoup(r.text, "html.parser")
    for carte in soup.select("div.search-item"):
        info = carte.select_one("div.search-info")
        onclick = carte.get("onclick") or ""
        m_id = re.search(r"/(\d+)-", onclick)
        if not info or not m_id:
            continue
        # the title without the date: "One Piece (1999)" -> "One Piece"
        m_titre = re.search(r"[^()]+", info.get_text(strip=True))
        if not m_titre:
            continue
        titre = m_titre.group(0).strip()
        # the series name without "- Saison N ...": the site then returns all its seasons
        titre_base = re.sub(r"\s*[-:]\s*Saison\s*\d+.*$", "", titre, flags=re.I).strip() or titre
        # the URL carries the anime's name: it is all that reaches expand_frenchmanga_url
        url = f"{base_site}/{m_id.group(1)}-x.html?" + urlencode({"title_base": titre_base})

        # match_title: the series name, without "- Saison N" (the fallback compares it with Sonarr's title)
        resultats.append({"title": titre, "url": url, "support": "Anime Supported", "site": "french-manga",
                          "match_title": titre_base})

    return resultats

def _merge_same_series(results):
    """One result per series.

    The site lists every season (and film) of a series as its own search result, and
    expanding any of them returns all the seasons of the series: without merging, the
    user would pick "Saison 1" in the search and then be asked again which season.

    Results are grouped by series name (match_title). A name that is the same as another
    one followed by a dash or a colon ("Saga of Tanya the Evil" / "Saga of Tanya the Evil -
    the Movie -", "Detective Conan" / "Detective Conan : Le Sous-Marin Noir") belongs to
    that series; "Naruto" / "Naruto Shippuden" stays two series."""
    bases = sorted({r["match_title"] for r in results}, key=len)

    def series_of(base):
        for candidate in bases:
            if candidate != base and base.startswith(candidate) and re.match(r"\s*[-–—:]", base[len(candidate):]):
                return candidate
        return base

    groups, order = {}, []
    for r in results:
        key = series_of(r["match_title"])
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(r)

    merged = []
    for key in order:
        members = groups[key]
        head = next((m for m in members if m["match_title"] == key), None)
        if head is None:
            # no result carries the series name itself: build it from the first one,
            # which keeps its id (the site only needs title_base to list the seasons)
            first = members[0]
            m_id = re.search(r"/(\d+)-", first["url"])
            head = dict(first)
            head["match_title"] = key
            if m_id:
                head["url"] = first["url"].split("?", 1)[0] + "?" + urlencode({"title_base": key})
        merged.append({**head, "title": key})
    return merged


def search_frenchmanga(queries, headers=None):
    queries = [queries] if isinstance(queries, str) else queries
    return _merge_same_series(_dedupe([r for q in queries for r in _search_frenchmanga_one(q, headers)]))
