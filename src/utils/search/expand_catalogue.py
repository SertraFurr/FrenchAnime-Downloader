"""Seasons of an anime.

The code specific to each site is in src/sites/<site>/seasons.py; only the
dispatch remains here: the site is recognized by its URL.
"""
from src.sites import site_for_url

# Former names, kept for the modules that still import them (main.py, the fallback).
from src.sites.nakanime.crypto import NAKANIME_DOMAIN, cO, derive_nakanime_key, decode_nakanime_response
from src.sites.nakanime.seasons import expand_nakanime_url
from src.sites.franime.seasons import (
    extract_franime_id, extract_franime_season, find_franime_anime, extraire_numero,
    trouver_position_saison, expand_franime_url,
)
from src.sites.french_manga.seasons import (
    get_frenchmanga_seasons, extract_frenchmanga_title_base, expand_frenchmanga_url,
)
from src.sites.anime_sama.seasons import is_valid_season, is_real_url, get_matches_from_page


def expand_catalogue_url(url, headers=None):
    site = site_for_url(url)
    return site.expand(url, headers) if site.expand else []
