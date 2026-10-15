"""Nakanime: a site of the program (see src/sites/base.py)."""
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
from src.sites.nakanime.search import search_nakanime
from src.sites.nakanime.seasons import expand_nakanime_url
from src.sites.nakanime.episodes import fetch_nakanime_episodes, fetch_nakanime_episode_count
from src.sites.nakanime import metadata

SITE = Site(
    key="nakanime",
    name="Nakanime",
    order=1,
    domains=("nakanime.tv", "nakanime.fr"),
    search=search_nakanime,
    expand=expand_nakanime_url,
    fetch_episodes=fetch_nakanime_episodes,
    episode_count=fetch_nakanime_episode_count,
    anime_name=metadata.anime_name,
    alt_titles=metadata.alt_titles,
    season_info=metadata.season_info,
    season_url_pattern=re.compile(r'^https?://(?:www\.)?nakanime\.tv/(?:anime/\d+|catalog\?.*overlay=).*$', re.IGNORECASE),
    url_example="https://nakanime.tv/anime/<id>/season/<s_num>/episode/<ep_num>",
)
