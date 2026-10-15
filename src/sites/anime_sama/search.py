"""Anime-Sama: search."""
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

def check_link_support(res, headers):
    try:
        from src.sites.anime_sama.seasons import is_valid_season
        
        r = requests.get(res['url'], headers=headers, timeout=5)
        if r.status_code == 200:
            content = r.text
            
            anime_matches = re.findall(r'panneauAnime\s*\(\s*(["\'])(.*?)\1\s*,\s*(["\'])(.*?)\3\s*\)', content)
            
            has_valid_anime = False
            
            base_url = res['url']
            if not base_url.endswith('/'):
                base_url += '/'

            for _, name, _, rel_url in anime_matches:
                if name == "nom" or rel_url == "url": continue
                
                full_url = urljoin(base_url, rel_url)
                if not full_url.endswith('/'): full_url += '/'
                
                if is_valid_season(full_url, headers):
                    has_valid_anime = True
                    break
            
            if has_valid_anime:
                scan_matches = re.findall(r'panneauScan\s*\(\s*(["\'])(.*?)\1\s*,\s*(["\'])(.*?)\3\s*\)', content)
                valid_scan = [m for m in scan_matches if m[1] != "nom" and m[3] != "url"]
                
                if valid_scan:
                    res['support'] = "Anime & Scans Supported"
                else:
                    res['support'] = "Anime Supported"
            else:
                scan_matches = re.findall(r'panneauScan\s*\(\s*(["\'])(.*?)\1\s*,\s*(["\'])(.*?)\3\s*\)', content)
                valid_scan = [m for m in scan_matches if m[1] != "nom" and m[3] != "url"]
                
                if valid_scan:
                    res['support'] = "Scans Supported"
                else:
                    res['support'] = "Unsupported"
        else:
            res['support'] = "Unknown"
    except Exception:
        res['support'] = "Unknown"
    return res

def _search_anime_sama_one(query, headers=None):
    url = f"https://{get_domain()}/template-php/defaut/fetch.php"

    data = {"query": query}
    
    try:
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        for a in soup.find_all('a'):
            href = a.get('href')
            h3 = a.find('h3')
            title = h3.text.strip() if h3 else "Unknown"
            if href:
                full_url = urljoin(f"https://{get_domain()}/", href)
                results.append({"title": title, "url": full_url, "support": None, "site": "anime-sama"})
        
        return results
    except Exception:
        return []

def search_anime_sama(queries, headers=None):
    queries = [queries] if isinstance(queries, str) else queries
    results = _dedupe([r for q in queries for r in _search_anime_sama_one(q, headers)])
    if results:
        with ThreadPoolExecutor(max_workers=10) as executor:
            list(executor.map(lambda r: check_link_support(r, headers), results))
    return results
