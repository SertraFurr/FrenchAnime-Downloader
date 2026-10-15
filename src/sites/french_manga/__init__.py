"""french-manga: a site of the program (see src/sites/base.py)."""
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
from src.sites.base import Site
from src.sites.french_manga.search import search_frenchmanga
from src.sites.french_manga.seasons import expand_frenchmanga_url
from src.sites.french_manga.episodes import fetch_frenchmanga_episodes, fetch_frenchmanga_episode_count
from src.sites.french_manga import metadata

SITE = Site(
    key="french-manga",
    name="French-Manga",
    order=3,
    domains=("french-manga.net",),
    search=search_frenchmanga,
    expand=expand_frenchmanga_url,
    fetch_episodes=fetch_frenchmanga_episodes,
    episode_count=fetch_frenchmanga_episode_count,
    anime_name=metadata.anime_name,
    alt_titles=metadata.alt_titles,
    season_info=metadata.season_info,
    # a season page; the search URL carries ?title_base=... and is therefore not one
    season_url_pattern=re.compile(r'^https?://(?:[\w-]+\.)?french-manga\.net/(?:manga-streaming-\d+/)?\d+-[^/?#]+\.html$', re.IGNORECASE),
    url_example="https://w16.french-manga.net/manga-streaming-1/<id>-<nom>.html",
)
