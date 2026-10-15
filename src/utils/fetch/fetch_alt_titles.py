"""Alternate titles of an anime (useful to identify it on TVDB / IMDb).

The code specific to each site is in src/sites/<site>/metadata.py.
"""
from src.sites import site_for_url


def fetch_alt_titles(base_url, headers=None):
    site = site_for_url(base_url)
    if site.alt_titles:
        return site.alt_titles(base_url, headers)
    return []
