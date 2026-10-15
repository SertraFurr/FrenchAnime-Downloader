"""Title of an anime from its URL.

The code specific to each site is in src/sites/<site>/metadata.py.
"""
from src.sites import site_for_url


def extract_anime_name(base_url):
    site = site_for_url(base_url)
    if site.anime_name:
        return site.anime_name(base_url) or "episode"
    return "episode"
