"""HeyBox (xiaohiehe) wishlist client.

Fetches a user's game wishlist from the HeyBox web API. The endpoint requires
a valid ``hkey`` signature (see :mod:`hey2steam.signing`) plus the target
user's ``heybox_id``.
"""

import random
import string
import urllib.parse

import requests

from . import config, signing
from .errors import HeyBoxError

HEYBOX_BASE = "https://api.xiaoheihe.cn"
WISHLIST_PATH = "/game/get_game_list_v3"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.xiaoheihe.cn/",
}


def _random_device_id():
    """Generate a random 32-hex-char device id, matching HeyBox's format."""
    return "".join(random.choices(string.hexdigits.lower(), k=32))


def _build_url(heybox_id, imei, sign_algo):
    """Construct the signed wishlist request URL."""
    sig = signing.create_signature(WISHLIST_PATH, sign_algo)
    params = {
        "filter_tag": "all",
        "sort_type": "heybox_wish",
        "filter_platform": "all",
        "only_chinese": "0",
        "filter_release": "all",
        "filter_steam_deck": "all",
        "filter_version": "all",
        "filter_head": "pc",
        "show_dlc": "0",
        "filter_os": "all",
        "filter_family_share": "all",
        "filter_library": "no",
        "offset": "0",
        "limit": "500",
        "heybox_id": str(heybox_id),
        "imei": imei,
        "device_info": "Chrome",
        "nonce": sig["nonce"],
        "hkey": sig["hkey"],
        "os_type": "web",
        "x_os_type": "Windows",
        "x_client_type": "web",
        "os_version": "13",
        "version": "999.0.4",
        "build": "883",
        "_time": str(sig["_time"]),
        "dw": "393",
        "channel": "heybox_google",
        "x_app": "heybox",
    }
    query = urllib.parse.urlencode(params)
    return f"{HEYBOX_BASE}{WISHLIST_PATH}/?{query}"


def _as_int(value):
    """Coerce a value to int, returning None if it is not numeric."""
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _extract_appid(item):
    """Best-effort extraction of the Steam appid from a HeyBox game object.

    HeyBox exposes the Steam appid under several possible keys. We try them
    in order of confidence and return the first numeric value found.
    """
    for key in ("steam_appid", "appid", "steam_id", "steam_app_id"):
        if key in item:
            value = _as_int(item.get(key))
            if value:
                return value
    return None


def _extract_name(item):
    for key in ("game_name", "name", "title", "english_name"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _parse_wishlist(data):
    """Parse a ``get_game_list_v3`` response into a list of ``{appid, name}``."""
    if not isinstance(data, dict):
        raise HeyBoxError("Unexpected HeyBox response: not a JSON object")

    result = data.get("result", data)
    games = None

    if isinstance(result, dict):
        for key in ("games", "game_list", "list", "items"):
            candidate = result.get(key)
            if isinstance(candidate, list):
                games = candidate
                break
    elif isinstance(result, list):
        games = result

    if games is None:
        games = []

    items = []
    for game in games:
        if not isinstance(game, dict):
            continue
        appid = _extract_appid(game)
        if appid:
            items.append({"appid": appid, "name": _extract_name(game), "raw": game})
    return items


def fetch_wishlist(
    heybox_id,
    imei=None,
    pkey=None,
    sign_algo=None,
    timeout=20,
):
    """Fetch and parse the HeyBox wishlist for ``heybox_id``.

    ``imei`` is an optional device identifier; a random one is generated when
    omitted. ``pkey`` is only needed when the wishlist is private (it is sent
    as a cookie when provided).
    """
    if not heybox_id:
        raise HeyBoxError("heybox_id is required")

    algo = sign_algo or config.get("HEYBOX_SIGN_ALGO", "web")
    device_id = imei or config.get("HEYBOX_IMEI") or _random_device_id()

    cookies = {}
    if pkey:
        cookies["pkey"] = pkey

    url = _build_url(heybox_id, device_id, algo)
    try:
        resp = requests.get(url, headers=DEFAULT_HEADERS, cookies=cookies, timeout=timeout)
    except requests.RequestException as exc:
        raise HeyBoxError(f"HeyBox request failed: {exc}") from exc

    if resp.status_code != 200:
        raise HeyBoxError(f"HeyBox returned HTTP {resp.status_code}")

    try:
        data = resp.json()
    except ValueError as exc:
        raise HeyBoxError("HeyBox returned non-JSON content") from exc

    # Some errors are returned with a 200 status and a non-"ok" status field.
    status = data.get("status") if isinstance(data, dict) else None
    if status is not None and status != "ok":
        msg = data.get("msg") or data.get("message") or status
        raise HeyBoxError(f"HeyBox API error: {msg}")

    return _parse_wishlist(data)
