"""Player links of every episode of a season.

The code specific to each site is in src/sites/<site>/episodes.py; only the
dispatch remains here: the site is recognized by its URL.
"""
from src.sites import site_for_url

# Former names, kept for the modules that still import them (main.py, the fallback).
from src.sites.nakanime.crypto import NAKANIME_DOMAIN, cO, derive_nakanime_key, decode_nakanime_response
from src.sites.nakanime.episodes import (
    _get_nakanime_session_and_headers, _get_nakanime_episode_numbers, NAKANIME_SOURCES_PATH,
    _fetch_nakanime_sources, fetch_nakanime_available_count, fetch_nakanime_episode_count,
    fetch_nakanime_episodes,
)
from src.sites.franime.episodes import (
    FRANIME_DOMAIN, FRANIME_API, FRANIME_API_HEADERS, FRANIME_TEST_URL, FRANIME_LANG_NAMES, _PRINTABLE,
    decode_franime_watch_url, _franime_request_args, _FRANIME_MIN_GAP, _franime_throttled,
    _franime_last_call, _franime_get, get_franime_players, build_franime_players,
    _franime_season_episodes, fetch_franime_episode_count, fetch_franime_episodes,
)
from src.sites.french_manga.episodes import (
    _frenchmanga_site, fetch_frenchmanga_episodes, fetch_frenchmanga_episode_count,
)
from src.sites.anime_sama.episodes import fetch_anime_sama_episodes


def fetch_episodes(base_url, headers=None, wanted_episodes=None):
    site = site_for_url(base_url)
    return site.fetch_episodes(base_url, headers, wanted_episodes=wanted_episodes)
