"""Anime-Sama: a site of the program (see src/sites/base.py)."""
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
from src.sites.anime_sama.search import search_anime_sama
from src.sites.anime_sama.seasons import expand_anime_sama_url
from src.sites.anime_sama.episodes import fetch_anime_sama_episodes
from src.sites.anime_sama import metadata

SITE = Site(
    key="anime-sama",
    name="Anime-Sama",
    order=0,
    domains=(),    # default site: any URL the other sites do not recognize
    search=search_anime_sama,
    expand=expand_anime_sama_url,
    fetch_episodes=fetch_anime_sama_episodes,
    anime_name=metadata.anime_name,
    alt_titles=metadata.alt_titles,
    season_info=metadata.season_info,
    season_url_pattern=re.compile(r'^https?://(?:www\.)?anime-sama\.[^/]+/catalogue/[^/]+/.+/.+/?$', re.IGNORECASE),
    url_example=f"https://{get_domain()}/catalogue/<anime-name>/<season-type>/<language>/",
)
