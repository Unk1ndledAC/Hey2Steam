"""HeyBox (xiaohiehe) wishlist client.

The HeyBox web API does not expose a user's wishlist as a single endpoint.
Instead, each game's follow state is public per ``heybox_id`` and can be
queried in bulk via ``/game/get_game_infos``. A user's wishlist is therefore
recovered by scanning the Steam app list and keeping every game whose
``follow_state`` is ``"following"``.

That scan needs the full Steam app list as input. It can be supplied directly
(``appids``), loaded from a local cache (``data/steam_games.json``, refreshed
by the daily GitHub workflow), or fetched live via ``steam.get_app_list``.
"""

import json
import random
import string
from pathlib import Path

import requests

from . import config, signing
from .errors import HeyBoxError

HEYBOX_BASE = "https://api.xiaoheihe.cn"
GAME_INFOS_PATH = "/game/get_game_infos"

# Number of appids to query per /game/get_game_infos request.
BATCH_SIZE = 200

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


def _as_int(value):
    """Coerce a value to int, returning None if it is not numeric."""
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _normalize_appids(appids):
    """Return a list of int appids from an int/``{appid, name}`` iterable."""
    ids = []
    for item in appids or []:
        value = item.get("appid") if isinstance(item, dict) else item
        value = _as_int(value)
        if value:
            ids.append(value)
    return ids


def get_game_infos(appids, heybox_id, device_id, sign_algo, cookies, timeout):
    """Batch-query the follow state of ``appids`` for ``heybox_id``.

    Returns a dict ``{appid: (follow_state, name)}``. The endpoint is public
    (no login required); ``cookies`` is passed through for completeness.
    """
    sig = signing.create_signature(GAME_INFOS_PATH, sign_algo)
    params = {
        "os_type": "web",
        "app": "heybox",
        "client_type": "web",
        "version": "999.0.4",
        "web_version": "2.5",
        "x_client_type": "web",
        "x_app": "heybox_website",
        "heybox_id": str(heybox_id),
        "x_os_type": "Windows",
        "device_info": "Chrome",
        "device_id": device_id,
        "hkey": sig["hkey"],
        "_time": str(sig["_time"]),
        "nonce": sig["nonce"],
        "appids": ",".join(str(a) for a in appids),
    }
    url = f"{HEYBOX_BASE}{GAME_INFOS_PATH}"
    try:
        resp = requests.get(
            url, params=params, headers=DEFAULT_HEADERS, cookies=cookies, timeout=timeout
        )
    except requests.RequestException as exc:
        raise HeyBoxError(f"HeyBox request failed: {exc}") from exc

    if resp.status_code != 200:
        raise HeyBoxError(f"HeyBox returned HTTP {resp.status_code}")

    try:
        data = resp.json()
    except ValueError as exc:
        raise HeyBoxError("HeyBox returned non-JSON content") from exc

    result = data.get("result") or {}
    base_infos = result.get("base_infos") or []
    out = {}
    for info in base_infos:
        if not isinstance(info, dict):
            continue
        appid = _as_int(info.get("steam_appid", info.get("appid")))
        if not appid:
            continue
        out[appid] = (info.get("follow_state"), info.get("name", ""))
    return out


def load_cached_games(path=None):
    """Load cached Steam games (``{appid, name}``) from ``data/steam_games.json``.

    Returns a list of ``{appid, name}`` dicts, or ``None`` when the cache is
    missing or unreadable. Used to resolve game names for the diff view.
    """
    path = Path(path) if path else config.PROJECT_ROOT / "data" / "steam_games.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None
    apps = data.get("apps") if isinstance(data, dict) else data
    out = []
    for item in apps or []:
        if not isinstance(item, dict):
            continue
        appid = _as_int(item.get("appid"))
        if not appid:
            continue
        out.append({"appid": appid, "name": item.get("name", "")})
    return out or None


def load_cached_appids(path=None):
    """Load cached Steam appids from ``data/steam_games.json``.

    Returns a list of int appids, or ``None`` when the cache is missing or
    unreadable. The cache is produced by ``scripts/update_game_list.py``.
    """
    games = load_cached_games(path)
    if games is None:
        return None
    return [g["appid"] for g in games]


def fetch_wishlist(
    heybox_id,
    appids=None,
    imei=None,
    pkey=None,
    sign_algo=None,
    timeout=20,
):
    """Fetch the HeyBox wishlist for ``heybox_id``.

    The wishlist is recovered by scanning ``appids`` (the Steam app list) and
    keeping every game whose ``follow_state`` is ``"following"``. When
    ``appids`` is ``None``, the local cache ``data/steam_games.json`` is used;
    if that is also absent an error is raised (provide ``appids`` or run the
    daily update script / pass a Steam API key to the caller).

    ``imei`` is an optional device id (auto-generated when omitted). ``pkey``
    is only needed for private data and is sent as a cookie when provided.
    """
    if not heybox_id:
        raise HeyBoxError("heybox_id is required")

    if appids is None:
        appids = load_cached_appids()
    ids = _normalize_appids(appids)
    if not ids:
        raise HeyBoxError(
            "No Steam app list available to scan. Provide appids, or run the "
            "daily update script (scripts/update_game_list.py), or pass a "
            "Steam API key so the app list can be fetched live."
        )

    algo = sign_algo or config.get("HEYBOX_SIGN_ALGO", "web")
    device_id = imei or config.get("HEYBOX_IMEI") or _random_device_id()

    cookies = {}
    if pkey:
        cookies["pkey"] = pkey

    following = []
    for start in range(0, len(ids), BATCH_SIZE):
        chunk = ids[start : start + BATCH_SIZE]
        states = get_game_infos(chunk, heybox_id, device_id, algo, cookies, timeout)
        for appid, (state, name) in states.items():
            if state == "following":
                following.append({"appid": appid, "name": name})
    return following
