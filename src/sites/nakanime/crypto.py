"""Nakanime: API response encryption (XOR with a key derived from the path)."""
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

NAKANIME_DOMAIN = "nakanime.tv"

cO = "nkapiv1"

def derive_nakanime_key(url_path):
    N = cO + url_path
    V = []
    for v in range(32):
        G = 0
        for q in range(len(N)):
            G = (G * 31 + ord(N[q]) + v) & 255
        V.append(G)
    return V

def decode_nakanime_response(response_bytes, url_path):
    key_bytes = derive_nakanime_key(url_path)
    out = bytearray(len(response_bytes))
    for i in range(len(response_bytes)):
        out[i] = response_bytes[i] ^ key_bytes[i % len(key_bytes)]
    return bytes(out)
