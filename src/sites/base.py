"""Description of a site (a source): everything the program knows how to do with it.

To add a site: create a src/sites/<site>/ folder whose __init__.py defines
SITE = Site(...), then add it to the SITES list of src/sites/__init__.py.
"""
from dataclasses import dataclass
from typing import Callable, Optional, Pattern, Tuple


@dataclass
class Site:
    key: str                         # internal name, lowercase ("franime")
    name: str                        # display name ("FRAnime")
    order: int                       # position in the search results
    domains: Tuple[str, ...] = ()    # URL fragments that identify this site (empty = default site)
    search: Optional[Callable] = None          # (queries, headers) -> [{"title","url","support","site"}]
    expand: Optional[Callable] = None          # (url, headers) -> [{"name": "Saison N", "url": ...}]
    fetch_episodes: Optional[Callable] = None  # (base_url, headers, wanted_episodes) -> {"Lecteur (LANGUE)": [liens]}
    episode_count: Optional[Callable] = None   # (base_url, headers) -> int | None   (optional)
    anime_name: Optional[Callable] = None      # (base_url) -> str
    alt_titles: Optional[Callable] = None      # (base_url, headers) -> [str]
    season_info: Optional[Callable] = None     # (base_url) -> "saisonN"
    season_url_pattern: Optional[Pattern] = None   # matches a SEASON URL
    url_example: str = ""                          # example shown in the error message

    def matches(self, url):
        u = (url or "").lower()
        return any(d in u for d in self.domains)
