"""Orchestration: sync a HeyBox wishlist into a Steam wishlist."""

from . import heybox, steam
from .errors import ConfigError


def resolve_appids(game_appids, steam_api_key):
    """Resolve the Steam app list used to scan HeyBox follow states.

    Priority: an explicit ``game_appids``, then the local cache
    (``data/steam_games.json``), then a live fetch via ``steam_api_key``.
    Returns a list of int appids.
    """
    if game_appids:
        ids = []
        for item in game_appids:
            value = item.get("appid") if isinstance(item, dict) else item
            try:
                value = int(value)
            except (TypeError, ValueError):
                continue
            if value:
                ids.append(value)
        return ids

    cached = heybox.load_cached_appids()
    if cached:
        return cached

    if steam_api_key:
        return [a["appid"] for a in steam.get_app_list(steam_api_key)]

    return []


def build_name_map(game_appids=None):
    """Build an ``{appid: name}`` map from ``game_appids`` or the local cache.

    Used to resolve display names for Steam-only games (Steam's wishlist API
    does not return game names).
    """
    items = game_appids if game_appids else heybox.load_cached_games()
    mapping = {}
    for item in items or []:
        if isinstance(item, dict) and item.get("appid"):
            mapping[int(item["appid"])] = item.get("name", "")
    return mapping


def compute_diff(heybox_items, steam_appids, name_map=None):
    """Compute the bidirectional diff between HeyBox and Steam wishlists.

    Returns a dict with ``heybox_only`` (on HeyBox, missing on Steam),
    ``steam_only`` (on Steam, missing on HeyBox), ``both_count``, and the two
    totals.
    """
    hb = {item["appid"]: item for item in heybox_items}
    st = set(steam_appids)

    heybox_only = [hb[a] for a in hb if a not in st]
    steam_only = [
        {"appid": a, "name": (name_map or {}).get(a, "")}
        for a in sorted(a for a in st if a not in hb)
    ]

    return {
        "heybox_only": heybox_only,
        "steam_only": steam_only,
        "both_count": len(hb) - len(heybox_only),
        "heybox_total": len(hb),
        "steam_total": len(st),
    }


def apply_changes(to_add, to_remove, steam_access_token, dry_run=False, progress=None):
    """Apply a set of wishlist changes (adds and removes).

    ``to_add`` and ``to_remove`` are iterables of ``{appid, name}`` dicts.
    Returns a dict with ``added``, ``removed``, ``failed_add``,
    ``failed_remove`` and ``dry_run``.
    """
    def _report(stage, detail):
        if progress:
            progress(stage, detail)

    added, removed = [], []
    failed_add, failed_remove = [], []

    for index, item in enumerate(to_add or [], start=1):
        _report("add", f"{index}/{len(to_add)}: {item.get('name') or item['appid']}")
        if dry_run:
            added.append(item)
            continue
        try:
            steam.add_to_wishlist(item["appid"], access_token=steam_access_token)
            added.append(item)
        except Exception as exc:  # noqa: BLE001 — report per-item failures
            failed_add.append({**item, "error": str(exc)})

    for index, item in enumerate(to_remove or [], start=1):
        _report("remove", f"{index}/{len(to_remove)}: {item.get('name') or item['appid']}")
        if dry_run:
            removed.append(item)
            continue
        try:
            steam.remove_from_wishlist(item["appid"], access_token=steam_access_token)
            removed.append(item)
        except Exception as exc:  # noqa: BLE001
            failed_remove.append({**item, "error": str(exc)})

    _report("done", "Changes applied")
    return {
        "added": added,
        "removed": removed,
        "failed_add": failed_add,
        "failed_remove": failed_remove,
        "dry_run": dry_run,
    }


def sync(
    heybox_id,
    steamid,
    steam_access_token=None,
    steam_api_key=None,
    game_appids=None,
    heybox_imei=None,
    heybox_pkey=None,
    sign_algo=None,
    dry_run=False,
    progress=None,
):
    """Sync the HeyBox wishlist into Steam (add-only) and return a report.

    Parameters:
        heybox_id:         HeyBox user ID whose wishlist is the source.
        steamid:           64-bit Steam ID that owns the destination wishlist.
        steam_access_token: webapi_token, required to actually add items.
        steam_api_key:     Optional Web API key for reading Steam data and for
                           fetching the app list when no cache exists.
        game_appids:       Optional Steam app list used to scan HeyBox follow
                           states (list of int or ``{appid, name}`` dicts).
        heybox_imei:       Optional HeyBox device id (auto-generated if None).
        heybox_pkey:       Optional HeyBox login credential for private lists.
        sign_algo:         "web" (default) or "chat" HeyBox signature variant.
        dry_run:           When True, compute the diff without writing anything.
        progress:          Optional callable invoked as ``progress(stage, detail)``.

    Returns:
        A dict with keys: ``heybox_total``, ``already_on_steam``, ``added``,
        ``failed``, ``dry_run``.
    """
    def _report(stage, detail):
        if progress:
            progress(stage, detail)

    _report("apps", "Resolving the Steam app list...")
    appids = resolve_appids(game_appids, steam_api_key)
    if not appids:
        raise ConfigError(
            "No Steam app list available. Provide game_appids, a Steam API "
            "key, or run the daily update script first."
        )

    _report("heybox", "Scanning HeyBox follow states...")
    heybox_items = heybox.fetch_wishlist(
        heybox_id,
        appids=appids,
        imei=heybox_imei,
        pkey=heybox_pkey,
        sign_algo=sign_algo,
    )

    _report("steam", "Fetching current Steam wishlist...")
    existing = set(steam.get_wishlist(steamid, api_key=steam_api_key))

    wanted = [item for item in heybox_items if item["appid"] not in existing]

    added = []
    failed = []
    for index, item in enumerate(wanted, start=1):
        _report("add", f"{index}/{len(wanted)}: {item['name'] or item['appid']}")
        if dry_run:
            added.append(item)
            continue
        try:
            steam.add_to_wishlist(item["appid"], access_token=steam_access_token)
            added.append(item)
        except Exception as exc:  # noqa: BLE001 — report per-item failures
            failed.append({**item, "error": str(exc)})

    _report("done", "Sync finished")
    return {
        "heybox_total": len(heybox_items),
        "already_on_steam": len(heybox_items) - len(wanted),
        "added": added,
        "failed": failed,
        "dry_run": dry_run,
    }
