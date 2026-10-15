"""french-manga: the requests to the site, with the Cloudflare cookie when there is one.

The site sits behind Cloudflare. From some connections a plain Python client gets
through; from others it receives a `403` "Just a moment". When the user has pasted
their cf_clearance cookie (main.py asks for it once) it is used here, with the
User-Agent that obtained it: the cookie is only valid with it.

The cookie is set on `.french-manga.net`: a single entry for every subdomain
(w16, w17...).
"""
import requests

from src.utils.config.config import get_domain_cookies

COOKIE_DOMAIN = "french-manga.net"

# A URL of the site that is under the Cloudflare rule, to test the cookie
# (the home page can answer 200 even with an expired cookie).
TEST_URL = "https://w16.french-manga.net/engine/ajax/get_seasons.php?title_base=One%20Piece"


def request_args():
    """(headers, cookies) to use. The caller's headers are never reused: they may carry
    another site's Cookie header, which requests would prefer over ours."""
    headers = {"User-Agent": "Mozilla/5.0"}
    cookies = None
    stored = get_domain_cookies(COOKIE_DOMAIN)
    if stored:
        cf_clearance, stored_headers = stored
        headers["User-Agent"] = stored_headers["User-Agent"]
        cookies = {"cf_clearance": cf_clearance}
    return headers, cookies


def get(url, **kwargs):
    headers, cookies = request_args()
    return requests.get(url, headers=headers, cookies=cookies, **kwargs)


def post(url, **kwargs):
    headers, cookies = request_args()
    return requests.post(url, headers=headers, cookies=cookies, **kwargs)
