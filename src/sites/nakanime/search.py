"""Nakanime: search."""
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
from src.sites._utils import dedupe as _dedupe
from src.sites.nakanime.crypto import derive_nakanime_key, decode_nakanime_response

def _search_nakanime_one(query, headers=None):
    encoded_query = urllib.parse.quote(query)
    path = f"/api/catalog/search?q={encoded_query}&sort=relevance&page=1&per_page=32"
    url = f"https://nakanime.tv{path}"
    
    req_headers = {"User-Agent": "Mozilla/5.0"}
    if headers and "User-Agent" in headers:
        req_headers["User-Agent"] = headers["User-Agent"]
        
    try:
        response = requests.get(url, headers=req_headers, timeout=10)
        response.raise_for_status()
        decrypted = decode_nakanime_response(response.content, path)
        data = json.loads(decrypted.decode('utf-8'))
        
        results = []
        for item in data.get('data', []):
            title = item.get('title', 'Unknown')
            anime_id = item.get('id')
            slug = item.get('slug')
            if anime_id and slug:
                full_url = f"https://nakanime.tv/anime/{anime_id}/{slug}"
                results.append({
                    "title": title,
                    "url": full_url,
                    "support": "Anime Supported",
                    "site": "nakanime"
                })
        return results
    except Exception as e:
        print_status(f"Nakanime search failed: {str(e)}", "warning")
        return []

def search_nakanime(queries, headers=None):
    queries = [queries] if isinstance(queries, str) else queries
    return _dedupe([r for q in queries for r in _search_nakanime_one(q, headers)])
