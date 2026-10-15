"""FRAnime: search."""
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
from src.sites.franime.catalogue import _fetch_franime_catalogue, texte

def _search_franime_one(query, headers=None):
    resultats=[]
    try:
         
        data = _fetch_franime_catalogue(headers)
        for a in data:
            if query.lower() in texte(a):
                resultats.append({"title":a["titleO"],"id":a["id"],"site":"franime","url":f"https://franime.fr/anime/test?anime_id={a['id']}","support":"Anime Supported"})

        return resultats

    except Exception as e: print(e); return []

def search_franime(queries, headers=None):
    queries = [queries] if isinstance(queries, str) else queries
    return _dedupe([r for q in queries for r in _search_franime_one(q, headers)])
