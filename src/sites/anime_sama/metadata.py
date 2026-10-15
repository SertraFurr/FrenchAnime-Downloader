"""Anime-Sama: anime title, alternate titles, season number."""
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

def anime_name(base_url):
    match = re.search(r'catalogue/([^/]+)/', base_url)
    return match.group(1) if match else "episode"

def alt_titles(base_url, headers=None):
    match = re.search(r'(https?://[^/]+/catalogue/[^/]+/)', base_url)
    if not match:
        return []
    root_url = match.group(1)

    try:
        response = requests.get(root_url, headers=headers, timeout=10)
        response.raise_for_status()
        html = response.text
    except requests.RequestException as e:
        print_status(f"Could not fetch alternate titles: {str(e)}", "warning")
        return []

    alt_match = re.search(r'id=["\']titreAlter["\'][^>]*>([^<]*)<', html)
    if not alt_match:
        return []

    return [title.strip() for title in alt_match.group(1).split(',') if title.strip()]

def season_info(base_url):
    # ".../catalogue/<anime>/saison1/vostfr/": the third piece from the end
    return base_url.split('/')[-3]
