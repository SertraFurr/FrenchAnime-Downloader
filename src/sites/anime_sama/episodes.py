"""Anime-Sama: the player links (the season's episodes.js file)."""
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

def fetch_anime_sama_episodes(base_url, headers=None, wanted_episodes=None):
    js_url = base_url.rstrip('/') + '/episodes.js'
    print_status("Fetching episode list...", "loading")
    try:
        response = requests.get(js_url, headers=headers, timeout=15)
        response.raise_for_status()
        js_content = response.text
    except Exception as e:
        print_status(f"Failed to fetch episodes.js: {str(e)}", "error")
        return None

    pattern = re.compile(r'var\s+(eps\d+)\s*=\s*\[([^\]]*)\];', re.MULTILINE)
    matches = pattern.findall(js_content)
    episodes = {}
    
    for name, content in matches:
        player_num = re.search(r'\d+', name).group()
        player_name = f"Player {player_num}"
        urls = re.findall(r"'(https?://[^']+)'", content)
        episodes[player_name] = urls
    
    if episodes:
        print_status(f"Found {len(episodes)} players with episodes!", "success")
    else:
        print_status("No episodes found in episodes.js", "error")
    
    return episodes
