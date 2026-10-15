"""Anime-Sama: the seasons of an anime (read from the catalogue page)."""
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

def is_valid_season(url, headers):
    try:
        ep_url = url.rstrip('/') + '/episodes.js'
        r = requests.get(ep_url, headers=headers, timeout=5)
        
        if r.status_code != 200:
            return False
            
        content = r.text
        if not content.strip():
            return False

        pattern = re.compile(r'var\s+eps\d+\s*=\s*\[(.*?)\];', re.DOTALL)
        array_matches = pattern.findall(content)
        
        if not array_matches:
            return False

        has_valid_url = False
        for array_content in array_matches:
            urls = re.findall(r"['\"](https?://[^'\"]+)['\"]", array_content)
            
            if any(is_real_url(u) for u in urls):
                has_valid_url = True
                break
                
        return has_valid_url
    except:
        return False

def is_real_url(u):
    u = u.strip()
    if len(u) < 20: return False
    
    if re.search(r'[?&][a-zA-Z0-9_]+=(?:$|&)', u):
        return False

    if re.search(r'/embed[-_.]?(?:\w{3,4})?$', u):
        return False
    
    return True

def get_matches_from_page(url, headers):
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        content = response.text

        content = re.sub(r'<!--[\s\S]*?-->', '', content)
        content = re.sub(r'/\*[\s\S]*?\*/', '', content)

        anime_matches = re.findall(r'panneauAnime\s*\(\s*(["\'])(.*?)\1\s*,\s*(["\'])(.*?)\3\s*\)', content)
        scan_matches = re.findall(r'panneauScan\s*\(\s*(["\'])(.*?)\1\s*,\s*(["\'])(.*?)\3\s*\)', content)
        
        results = []
        for _, name, _, rel_url in anime_matches:
            results.append((name, rel_url))
        for _, name, _, rel_url in scan_matches:
            results.append((name, rel_url))
            
        return results
    except Exception:
        return []

def expand_anime_sama_url(url, headers=None):
    raw_matches = get_matches_from_page(url, headers)
    
    if not raw_matches:
        domain = get_domain()
        match = re.search(r'https?://(?:www\.)?' + re.escape(domain) + r'/catalogue/([^/]+)/', url)
        if match:
            slug = match.group(1)
            root_url = f"https://{domain}/catalogue/{slug}/"
            if root_url.rstrip('/') != url.rstrip('/'):
                raw_matches = get_matches_from_page(root_url, headers)

    results = []
    seen_urls = set()
    
    for name, rel_url in raw_matches:
        if name == "nom" or rel_url == "url":
            continue
            
        full_url = urljoin(url if url.endswith('/') else url + '/', rel_url)
        if not full_url.endswith('/'):
            full_url += '/'
        
        if full_url in seen_urls:
            continue
        
        if '/scan' not in full_url.lower():
            if not is_valid_season(full_url, headers):
                continue
            
        seen_urls.add(full_url)
        results.append({"name": name, "url": full_url})
        
        if 'vostfr' in rel_url.lower():
            vf_rel = rel_url.lower().replace('vostfr', 'vf')
            vf_full = full_url.lower().replace('vostfr', 'vf')
            
            if vf_full not in seen_urls:
                if '/scan' not in vf_full:
                     if is_valid_season(vf_full, headers):
                        vf_name = f"{name} (VF)"
                        results.append({"name": vf_name, "url": vf_full})
                        seen_urls.add(vf_full)

    return results
