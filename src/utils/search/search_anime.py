"""Search for an anime on every site.

The code specific to each site is in src/sites/<site>/search.py; only what is
common remains here: split the query, run the sites in parallel, rank.
"""
import re
import difflib
from concurrent.futures import ThreadPoolExecutor

from src.sites import SITES
from src.sites._utils import dedupe as _dedupe

# Former names, kept for the modules that still import them (the fallback).
from src.sites.anime_sama.search import check_link_support, _search_anime_sama_one, search_anime_sama
from src.sites.nakanime.search import _search_nakanime_one, search_nakanime
from src.sites.franime.search import _search_franime_one, search_franime
from src.sites.franime.catalogue import _FRANIME_CACHE, _FRANIME_CACHE_SECONDS, _fetch_franime_catalogue, texte
from src.sites.french_manga.search import _search_frenchmanga_one, search_frenchmanga

def _keywords(query):
    """The full query plus each keyword alone, so 'king raid' also finds "King's Raid"."""
    words = [w for w in _norm(query).split() if len(w) >= 3]
    return [query] + [w for w in dict.fromkeys(words) if w != _norm(query)]

def _norm(text):
    return re.sub(r'[^a-z0-9 ]', '', text.lower().replace("'", "").replace("-", " "))

def relevance(query, title):
    q, t = _norm(query), _norm(title)
    if not q or not t:
        return 0.0
    t_tokens = t.split()
    q_tokens = [w for w in q.split() if len(w) >= 3] or q.split()
    positions = []
    for qt in q_tokens:
        pos = next((i for i, tt in enumerate(t_tokens) if tt.startswith(qt)), None)
        if pos is not None:
            positions.append(pos)
    covered = len(positions) / len(q_tokens)
    in_order = len(positions) == len(q_tokens) and positions == sorted(positions)
    ratio = difflib.SequenceMatcher(None, q.replace(" ", ""), t.replace(" ", "")).ratio()
    return max(covered * (0.9 if in_order else 0.7), ratio)

MIN_SCORE = 0.5

MIN_PER_SITE = 3

def rank_results(query, results):
    """Best match first inside each site; sites keep a fixed order (Anime-Sama, then Nakanime)."""
    by_site = {}
    for r in results:
        r['score'] = relevance(query, r['title'])
        by_site.setdefault(r.get('site') or '', []).append(r)
    groups = []
    for g in by_site.values():
        g = sorted(g, key=lambda r: -r['score'])
        groups.append([r for i, r in enumerate(g) if i < MIN_PER_SITE or r['score'] >= MIN_SCORE])
    order = {s.key: s.order for s in SITES}
    groups.sort(key=lambda g: order.get(g[0].get('site'), 99))
    return [r for g in groups for r in g]


def search_anime(query, headers=None, site="all"):
    queries = _keywords(query)
    # one given site (by its name), otherwise all of them
    chosen = [s for s in SITES if s.search and site and site.lower() == s.key] or [s for s in SITES if s.search]

    if len(chosen) == 1:
        return rank_results(query, chosen[0].search(queries, headers=headers))

    with ThreadPoolExecutor(max_workers=len(chosen)) as executor:
        futures = [executor.submit(s.search, queries, headers) for s in chosen]
        results = [r for f in futures for r in f.result()]

    return rank_results(query, results)
