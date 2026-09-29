"""Steam wishlist client.

Steam exposes wishlist data through two distinct mechanisms:

* **Reading** — ``IWishlistService/GetWishlist``, which works with a plain
  SteamID (public wishlists) and optionally a Web API key.
* **Writing** — adding/removing items requires *user authentication*. The Web
  API key alone cannot modify a wishlist. Two methods are supported:

  1. ``IWishlistService/AddToWishlist`` with a user **access token**
     (``webapi_token``). Get it by logging into Steam and opening
     ``https://store.steampowered.com/pointssummary/ajaxgetasyncconfig``;
     the token expires roughly every 24 hours.
  2. The legacy store endpoint ``store.steampowered.com/api/addtowishlist``
     with a ``sessionid`` cookie value.
"""

import requests

from .errors import SteamError

STEAM_API_BASE = "https://api.steampowered.com"
STEAM_STORE_BASE = "https://store.steampowered.com"

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
    """Add ``appid`` to the wishlist using a user access token."""
    url = f"{STEAM_API_BASE}/IWishlistService/AddToWishlist/v1/"
    data = {"access_token": access_token, "appid": str(appid)}
    resp = requests.post(url, data=data, timeout=timeout)
    resp.raise_for_status()
    return resp


def _add_via_store(appid, sessionid, timeout):
    """Add ``appid`` to the wishlist using the legacy store endpoint."""
    url = f"{STEAM_STORE_BASE}/api/addtowishlist"
    data = {"appid": str(appid), "sessionid": sessionid}
    resp = requests.post(url, data=data, timeout=timeout)
    resp.raise_for_status()
    return resp


def add_to_wishlist(appid, access_token=None, sessionid=None, timeout=TIMEOUT):
    """Add ``appid`` to the wishlist.

    Prefers the access-token method; falls back to the legacy session method.
    """
    try:
        if access_token:
            resp = _add_via_webapi(appid, access_token, timeout)
        elif sessionid:
            resp = _add_via_store(appid, sessionid, timeout)
        else:
            raise SteamError(
                "Adding to the wishlist requires an access token "
                "(webapi_token) or a sessionid"
            )
    except requests.RequestException as exc:
        raise SteamError(f"Steam add-to-wishlist failed: {exc}") from exc

    # Both endpoints signal success with HTTP 2xx and an optional JSON body.
    # If a body is present, treat an explicit "success" flag / EResult as the
    # source of truth.
    try:
        body = resp.json()
    except ValueError:
        body = None

    if isinstance(body, dict):
        if "success" in body:
            if body["success"] in (1, True, "1", "true"):
                return True
            raise SteamError(f"Steam refused to add appid {appid}: {body}")
        # AddToWishlist returns an EResult; EResult.OK == 1.
        if "result" in body and body["result"] not in (1, "1", None):
            raise SteamError(f"Steam EResult {body['result']} for appid {appid}")
    return True
