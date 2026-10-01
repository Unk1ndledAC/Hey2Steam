"""Steam wishlist client.

Steam exposes wishlist data through two distinct mechanisms:

* **Reading** — ``IWishlistService/GetWishlist``, which works with a plain
  SteamID (public wishlists) and optionally a Web API key.
* **Writing** — ``IWishlistService/AddToWishlist`` authenticated with a user
  **access token** (``webapi_token``). Get it by logging into Steam and
  opening ``store.steampowered.com/pointssummary/ajaxgetasyncconfig``; the
  token expires roughly every 24 hours. The Web API key cannot write.
"""

import requests

from .errors import SteamError

STEAM_API_BASE = "https://api.steampowered.com"

TIMEOUT = 20


def get_wishlist(steamid, api_key=None, timeout=TIMEOUT):
    """Return the list of appids currently on ``steamid``'s wishlist."""
    if not steamid:
        raise SteamError("steamid is required")
    params = {"steamid": str(steamid)}
    if api_key:
        params["key"] = api_key
    url = f"{STEAM_API_BASE}/IWishlistService/GetWishlist/v1/"
    try:
        resp = requests.get(url, params=params, timeout=timeout)
    except requests.RequestException as exc:
        raise SteamError(f"Steam request failed: {exc}") from exc

    if resp.status_code != 200:
        raise SteamError(f"Steam returned HTTP {resp.status_code}")

    try:
        data = resp.json()
    except ValueError as exc:
        raise SteamError("Steam returned non-JSON content") from exc

    response = data.get("response") or {}
    items = response.get("items") or []
    return [int(item["appid"]) for item in items if "appid" in item]


def _add_via_webapi(appid, access_token, timeout):
    """Add ``appid`` via ``IWishlistService/AddToWishlist`` with a user token.

    The access token (``webapi_token``) is passed as the ``access_token`` query
    parameter; ``appid`` goes in the form body. On success Steam returns
    ``{"response": {"wishlist_count": N}}``.
    """
    url = f"{STEAM_API_BASE}/IWishlistService/AddToWishlist/v1/"
    resp = requests.post(
        url,
        params={"access_token": access_token},
        data={"appid": str(appid)},
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp


def add_to_wishlist(appid, access_token, timeout=TIMEOUT):
    """Add ``appid`` to the wishlist using a user access token (``webapi_token``)."""
    if not access_token:
        raise SteamError(
            "Adding to the wishlist requires an access token (webapi_token)"
        )
    try:
        resp = _add_via_webapi(appid, access_token, timeout)
    except requests.RequestException as exc:
        raise SteamError(f"Steam add-to-wishlist failed: {exc}") from exc

    # The web API returns {"response": {"wishlist_count": N}} on success.
    try:
        body = resp.json()
    except ValueError:
        body = None

    if isinstance(body, dict) and "response" not in body:
        if body.get("success") is False:
            raise SteamError(f"Steam refused to add appid {appid}: {body}")
    return True


def get_app_list(api_key, timeout=TIMEOUT):
    """Return the full Steam store app list as ``[{appid, name}]``.

    Uses ``IStoreService/GetAppList`` (games only), paginated via
    ``last_appid``. Requires a Web API key (passed as the ``key`` parameter).
    """
    if not api_key:
        raise SteamError("A Steam Web API key is required to fetch the app list")
    url = f"{STEAM_API_BASE}/IStoreService/GetAppList/v1/"
    apps = []
    last_appid = 0
    while True:
        params = {
            "key": api_key,
            "include_games": "true",
            "include_dlc": "false",
            "include_software": "false",
            "include_videos": "false",
            "include_hardware": "false",
            "max_results": "50000",
            "format": "json",
        }
        if last_appid:
            params["last_appid"] = str(last_appid)
        try:
            resp = requests.get(url, params=params, timeout=timeout)
        except requests.RequestException as exc:
            raise SteamError(f"Steam app list request failed: {exc}") from exc
        if resp.status_code != 200:
            raise SteamError(f"Steam returned HTTP {resp.status_code}")
        try:
            data = resp.json()
        except ValueError as exc:
            raise SteamError("Steam returned non-JSON content") from exc
        response = data.get("response") or {}
        page = response.get("apps") or []
        for item in page:
            if isinstance(item, dict) and item.get("appid"):
                apps.append({"appid": int(item["appid"]), "name": item.get("name", "")})
        if not response.get("have_more_results") or not page:
            break
        next_appid = response.get("last_appid") or 0
        if next_appid <= last_appid:
            break
        last_appid = next_appid
    return apps


def remove_from_wishlist(appid, access_token, timeout=TIMEOUT):
    """Remove ``appid`` from the wishlist using a user access token.

    Mirrors ``add_to_wishlist``: the token is passed as the ``access_token``
    query parameter and ``appid`` goes in the form body.
    """
    if not access_token:
        raise SteamError(
            "Removing from the wishlist requires an access token (webapi_token)"
        )
    url = f"{STEAM_API_BASE}/IWishlistService/RemoveFromWishlist/v1/"
    try:
        resp = requests.post(
            url,
            params={"access_token": access_token},
            data={"appid": str(appid)},
            timeout=timeout,
        )
    except requests.RequestException as exc:
        raise SteamError(f"Steam remove-from-wishlist failed: {exc}") from exc

    if resp.status_code != 200:
        raise SteamError(f"Steam returned HTTP {resp.status_code}")

    try:
        body = resp.json()
    except ValueError:
        body = None

    if isinstance(body, dict) and "response" not in body:
        if body.get("success") is False:
            raise SteamError(f"Steam refused to remove appid {appid}: {body}")
    return True
