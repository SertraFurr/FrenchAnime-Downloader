import json
import os
import sys
import requests
from src.var import Colors, print_status

APP_NAME = "FrenchAnime-Downloader"
if os.name == "nt":
    CONFIG_ROOT = os.environ.get(
        "APPDATA",
        os.path.join(os.path.expanduser("~"), "AppData", "Roaming"),
    )
elif sys.platform == "darwin":
    CONFIG_ROOT = os.path.join(os.path.expanduser("~"), "Library", "Application Support")
else:
    CONFIG_ROOT = os.environ.get(
        "XDG_CONFIG_HOME",
        os.path.join(os.path.expanduser("~"), ".config"),
    )

CONFIG_PATH = os.path.join(CONFIG_ROOT, APP_NAME, "config.json")
LEGACY_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")


def _save_config(config):
    config_directory = os.path.dirname(CONFIG_PATH)
    os.makedirs(config_directory, exist_ok=True)

    temporary_path = CONFIG_PATH + ".tmp"
    try:
        with open(temporary_path, "w", encoding="utf-8") as config_file:
            json.dump(config, config_file, indent=4)
        if os.name != "nt":
            os.chmod(temporary_path, 0o600)
        os.replace(temporary_path, CONFIG_PATH)
    finally:
        if os.path.exists(temporary_path):
            os.remove(temporary_path)


def _load_config():
    if os.path.exists(CONFIG_PATH):
        config_path = CONFIG_PATH
    elif os.path.exists(LEGACY_CONFIG_PATH):
        config_path = LEGACY_CONFIG_PATH
    else:
        return {}

    with open(config_path, "r", encoding="utf-8") as config_file:
        config = json.load(config_file)
    if not isinstance(config, dict):
        raise ValueError(f"Expected a JSON object in config file: {config_path}")

    if config_path == LEGACY_CONFIG_PATH:
        _save_config(config)
    return config


def is_cloudflare_checks_enabled():
    return _load_config().get("cloudflare_checks_enabled", True) is not False


def get_cookies(include_disabled=False):
    config = _load_config()
    if not include_disabled and config.get("cloudflare_checks_enabled", True) is False:
        return False
    cf_clearance = config.get("cf_clearance_cookie", "")
    headers = config.get("headers", {})
    if not isinstance(headers, dict) or not cf_clearance or not headers.get("User-Agent"):
        return False
    return cf_clearance, headers


def set_cookies(cf_clearance_value, user_agent_value):
    config = _load_config()
    config["cf_clearance_cookie"] = cf_clearance_value
    config["headers"] = {"User-Agent": user_agent_value}
    _save_config(config)


def get_setting(key, default=None):
    return _load_config().get(key, default)


def set_setting(key, value):
    config = _load_config()
    config[key] = value
    _save_config(config)


def get_domain_cookies(domain, include_disabled=False):
    """Generic per-domain cf_clearance store (used for sites other than the
    main configured domain, e.g. nakanime.tv) - separate from the single
    cf_clearance_cookie/headers pair above so setting one site's cookie never
    overwrites another's."""
    config = _load_config()
    if not include_disabled and config.get("cloudflare_checks_enabled", True) is False:
        return False
    domain_cookies = config.get("domain_cookies", {})
    if not isinstance(domain_cookies, dict):
        return False
    entry = domain_cookies.get(domain)
    if not isinstance(entry, dict) or not entry.get("cf_clearance") or not entry.get("user_agent"):
        return False
    return entry["cf_clearance"], {"User-Agent": entry["user_agent"]}


def set_domain_cookies(domain, cf_clearance_value, user_agent_value):
    config = _load_config()
    store = config.setdefault("domain_cookies", {})
    if not isinstance(store, dict):
        raise ValueError("Expected 'domain_cookies' to be a JSON object in the config file")
    store[domain] = {"cf_clearance": cf_clearance_value, "user_agent": user_agent_value}
    _save_config(config)


def check_domain_cookies(domain, headers, test_url=None, extra_headers=None):
    """test_url: when the Cloudflare rule only covers part of the site (e.g.
    franime's API), check against a URL under that rule instead of the home
    page, which can answer 200 even with an expired cookie.

    Returns True (accepted), False (refused: 403, missing or mismatched) or
    None (could not reach the site, unknown)."""
    if not is_cloudflare_checks_enabled():
        return None

    stored = get_domain_cookies(domain)
    if stored is False:
        return False

    cf_clearance_value, stored_headers = stored

    if headers.get("User-Agent") != stored_headers.get("User-Agent"):
        return False

    request_headers = headers.copy()
    request_headers.update(extra_headers or {})
    request_headers['Cookie'] = f'cf_clearance={cf_clearance_value}'

    try:
        req = requests.get(test_url or f"https://{domain}", headers=request_headers, timeout=10)
        return req.status_code != 403
    except requests.RequestException:
        # Network hiccup (timeout, connection reset...): that says nothing about
        # the cookie. None = "could not check", callers must not treat it as
        # refused (a refused cookie gets erased).
        return None


def check_cookies(domain, headers):
    if not is_cloudflare_checks_enabled():
        return None

    stored = get_cookies()
    if stored is False:
        print_status("No Cloudflare cookie stored.", "error")
        return False

    cf_clearance_value, stored_headers = stored

    if headers.get("User-Agent") != stored_headers.get("User-Agent"):
        print_status(
            "Headers do not match the User-Agent used when the cookie was set. Please use the same User-Agent.",
            "error"
        )
        return False

    request_headers = headers.copy()
    request_headers['Cookie'] = f'cf_clearance={cf_clearance_value}'

    try:
        req = requests.get(f"https://{domain}", headers=request_headers, timeout=10)
        if req.status_code != 403:
            print_status("Cloudflare cookies are valid.", "success")
            return True
        else:
            print_status("Cloudflare cookies are invalid or expired.", "error")
            return False
    except requests.RequestException as e:
        print_status(f"Request failed: {e}", "error")
        return None   # unknown, not "refused": callers must not erase the cookie for this
