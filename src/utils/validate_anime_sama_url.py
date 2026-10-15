"""Is this URL the URL of a SEASON the program knows how to download?

Each site's pattern is in src/sites/<site>/__init__.py (season_url_pattern).
"""
from src.sites import SITES


def validate_anime_sama_url(url):
    for site in SITES:
        if site.season_url_pattern and site.season_url_pattern.match(url):
            return True, ""

    exemples = "".join(f"  {s.url_example}\n" for s in SITES if s.url_example)
    return False, f"{url} Invalid URL. Format should be:\n{exemples}"
