import re
import base64
import requests
from urllib.parse import urlparse

from src.utils.network.tls_compat import apply as _apply_tls
_apply_tls()

def unpack_packer(p, a, c, k, e=None, d=None):
    def baseN(num, b):
        return ((num == 0) and "0") or (baseN(num // b, b).lstrip("0") + "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"[num % b])
    
    k = k.split('|')
    while c:
        c -= 1
        key = baseN(c, a)
        if k[c]:
            p = re.sub(r'\b' + key + r'\b', k[c], p)
    return p

def decode_vidzy_src(encoded_str, key_bytes):
    raw = base64.b64decode(encoded_str)
    out = bytearray(len(raw))
    for i in range(len(raw)):
        out[i] = raw[i] ^ key_bytes[i % len(key_bytes)]
    return out.decode('utf-8', errors='replace')


def _decode_hidden_source(html, embed_url):
    """The real stream is not in the plain HTML: the page only leaves a ".../troll/master.m3u8"
    link in the clear (a clip of a few seconds) and hides the real one in an encrypted string
    that its JavaScript decrypts. Key = sum of the characters of the page's domain name + a
    width the browser measures on a CSS "calc(1in + Npx)" element (whose value changes on
    every load: it is read from the page, (96 + N) // 2)."""
    host = urlparse(embed_url).hostname or ""
    h = sum(ord(c) for c in host) & 255

    candidats = []
    # the main form: var E="...";function D(s){...calc(1in + Npx)...}
    for m in re.finditer(r'var E="([A-Za-z0-9+/=]{40,})";function D\(s\)\{.*?calc\(1in \+ (\d+)px\)', html, re.S):
        candidats.append((m.group(1), int(m.group(2))))
    # the inline form: (function(s){...calc(1in + Npx)...})("...")
    for m in re.finditer(r'calc\(1in \+ (\d+)px\).*?\}\)\("([A-Za-z0-9+/=]{40,})"\)', html, re.S):
        candidats.append((m.group(2), int(m.group(1))))

    for chaine, largeur in candidats:
        bc = (96 + largeur) // 2
        try:
            octets = base64.b64decode(chaine)[::-1]
        except Exception:
            continue
        url = "".join(chr(b ^ ((0x3d + i * 89 + h + bc) & 255)) for i, b in enumerate(octets))
        if re.match(r"^https?://", url) and "/troll/" not in url:
            return url
    return None


def extract_vidzy_video_source(url, headers=None):
    req_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://nakanime.tv/"
    }
    if headers:
        req_headers.update(headers)

    try:
        res = requests.get(url, headers=req_headers, timeout=10)
        if res.status_code != 200:
            return None

        # the real stream first: the first plain .m3u8 is often the "troll" clip
        hidden = _decode_hidden_source(res.text, url)
        if hidden:
            return hidden

        m3u8_matches = re.findall(r"['\"](https?://[^\s'\"]+\.m3u8[^\s'\"]*)['\"]", res.text)
        m3u8_matches = [m for m in m3u8_matches if "/troll/" not in m]
        if m3u8_matches:
            return m3u8_matches[0]

        pattern = r"eval\(function\(p,a,c,k,e,d\)\{.*?return p\}\('([\s\S]*?)',(\d+),(\d+),'([\s\S]*?)'\.split\('\|'\)"
        match = re.search(pattern, res.text)
        if match:
            p, a, c, k = match.group(1), int(match.group(2)), int(match.group(3)), match.group(4)
            unpacked = unpack_packer(p, a, c, k)
            
            key_match = re.search(r'var\s+k\s*=\s*\[([\d\s,]+)\]', unpacked)
            str_match = re.search(r'\}\)\(["\']([A-Za-z0-9+/=]+)["\']\)', unpacked)
            if key_match and str_match:
                key_list = [int(x.strip()) for x in key_match.group(1).split(',')]
                encoded_str = str_match.group(1)
                decoded_url = decode_vidzy_src(encoded_str, key_list)
                if decoded_url and "m3u8" in decoded_url:
                    return decoded_url

        return None
    except Exception:
        return None
