"""FRAnime: a site of the program (see src/sites/base.py)."""
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
from src.sites.franime.search import search_franime
from src.sites.franime.seasons import expand_franime_url
from src.sites.franime.episodes import fetch_franime_episodes, fetch_franime_episode_count
from src.sites.franime import metadata

SITE = Site(
    key="franime",
    name="FRAnime",
    order=2,
    domains=("franime.fr",),
    search=search_franime,
    expand=expand_franime_url,
    fetch_episodes=fetch_franime_episodes,
    episode_count=fetch_franime_episode_count,
    anime_name=metadata.anime_name,
    alt_titles=metadata.alt_titles,
    season_info=metadata.season_info,
    season_url_pattern=re.compile(r'^https?://(?:www\.)?franime\.fr/anime/[^/?]+\?.*anime_id=\d+.*$', re.IGNORECASE),
    url_example="https://franime.fr/anime/<nom>?s=<saison>&anime_id=<id>",
)
