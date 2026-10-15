"""The supported sites (sources). One folder per site: src/sites/<site>/.

Each folder contains:
    search.py     the search
    seasons.py    the seasons of an anime
    episodes.py   the player links of every episode
    metadata.py   the anime's title, its alternate titles, the season number
    __init__.py   SITE = Site(...): assembles all of the above (see base.py)

To add a site: create its folder, then add it to SITES below.
"""
from src.sites.base import Site
from src.sites import anime_sama, nakanime, franime, french_manga

# The order is the display order. anime_sama is the default site: a URL that no
# other site recognizes is handed to it.
SITES = [anime_sama.SITE, nakanime.SITE, franime.SITE, french_manga.SITE]
DEFAULT_SITE = anime_sama.SITE


def site_for_url(url):
    for site in SITES:
        if site.domains and site.matches(url):
            return site
    return DEFAULT_SITE


def site_by_key(key):
    for site in SITES:
        if site.key == (key or "").lower():
            return site
    return None
