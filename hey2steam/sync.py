"""Orchestration: sync a HeyBox wishlist into a Steam wishlist."""

from . import heybox, steam


def sync(
    heybox_id,
    steamid,
    steam_access_token=None,
    steam_api_key=None,
    steam_sessionid=None,
    heybox_imei=None,
    heybox_pkey=None,
    sign_algo=None,
    dry_run=False,
    progress=None,
):
    """Sync the HeyBox wishlist into Steam and return a structured report.

    Parameters:
        heybox_id:         HeyBox user ID whose wishlist is the source.
        steamid:           64-bit Steam ID that owns the destination wishlist.
        steam_access_token: webapi_token, required to actually add items.
        steam_api_key:     Optional Web API key for reading the Steam wishlist.
        steam_sessionid:   Optional legacy fallback for adding items.
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

    _report("heybox", "Fetching HeyBox wishlist...")
    heybox_items = heybox.fetch_wishlist(
        heybox_id,
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
            steam.add_to_wishlist(
                item["appid"],
                access_token=steam_access_token,
                sessionid=steam_sessionid,
            )
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
