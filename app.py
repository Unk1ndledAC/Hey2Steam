"""Flask web application for Hey2Steam.

Serves the bilingual web UI and exposes a small JSON API. The UI also works
standalone (client-side) when the static ``docs/index.html`` copy is hosted
without a backend; see the front-end for the auto-detection logic.

Run locally:
    python app.py
"""

import os
import sys

from flask import Flask, jsonify, request, send_from_directory

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from hey2steam import heybox, steam, sync  # noqa: E402

app = Flask(__name__)

# The web UI is a single self-contained HTML file. It is served here for the
# local Flask app and is the exact same file shipped as ``docs/index.html``
# for static GitHub Pages hosting.
DOCS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs")


@app.after_request
def _add_cors(resp):
    """Allow the hosted static page to reach a locally running backend.

    The GitHub Pages copy of the UI is served from a different origin than a
    local ``python app.py`` backend, so API responses must carry CORS headers.
    """
    resp.headers.setdefault("Access-Control-Allow-Origin", "*")
    resp.headers.setdefault("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    resp.headers.setdefault("Access-Control-Allow-Headers", "Content-Type")
    return resp


def _body():
    return request.get_json(silent=True) or {}


def _error(message, code):
    return jsonify({"error": message}), code


@app.route("/")
def index():
    return send_from_directory(DOCS_DIR, "index.html")


@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/api/heybox-wishlist", methods=["POST"])
def api_heybox_wishlist():
    body = _body()
    heybox_id = (body.get("heybox_id") or "").strip()
    if not heybox_id:
        return _error("heybox_id is required", 400)
    try:
        items = heybox.fetch_wishlist(
            heybox_id,
            imei=body.get("imei"),
            pkey=body.get("pkey"),
            sign_algo=body.get("sign_algo"),
        )
    except Exception as exc:  # noqa: BLE001
        return _error(str(exc), 502)
    return jsonify({"items": items, "count": len(items)})


@app.route("/api/steam-wishlist", methods=["POST"])
def api_steam_wishlist():
    body = _body()
    steamid = (body.get("steamid") or "").strip()
    if not steamid:
        return _error("steamid is required", 400)
    try:
        appids = steam.get_wishlist(steamid, api_key=body.get("api_key"))
    except Exception as exc:  # noqa: BLE001
        return _error(str(exc), 502)
    return jsonify({"appids": appids, "count": len(appids)})


@app.route("/api/sync", methods=["POST"])
def api_sync():
    body = _body()
    heybox_id = (body.get("heybox_id") or "").strip()
    steamid = (body.get("steamid") or "").strip()
    if not heybox_id:
        return _error("heybox_id is required", 400)
    if not steamid:
        return _error("steamid is required", 400)
    try:
        report = sync.sync(
            heybox_id=heybox_id,
            steamid=steamid,
            steam_access_token=body.get("steam_access_token"),
            steam_api_key=body.get("steam_api_key"),
            heybox_imei=body.get("heybox_imei"),
            heybox_pkey=body.get("heybox_pkey"),
            sign_algo=body.get("sign_algo"),
            dry_run=bool(body.get("dry_run")),
        )
    except Exception as exc:  # noqa: BLE001
        return _error(str(exc), 502)
    return jsonify(report)


@app.route("/api/diff", methods=["POST"])
def api_diff():
    body = _body()
    heybox_id = (body.get("heybox_id") or "").strip()
    steamid = (body.get("steamid") or "").strip()
    if not heybox_id:
        return _error("heybox_id is required", 400)
    if not steamid:
        return _error("steamid is required", 400)
    try:
        appids = sync.resolve_appids(body.get("game_appids"), body.get("steam_api_key"))
        if not appids:
            return _error(
                "No Steam app list available. Provide game_appids or "
                "steam_api_key, or run the daily update script first.",
                400,
            )
        name_map = sync.build_name_map(body.get("game_appids"))
        heybox_items = heybox.fetch_wishlist(
            heybox_id,
            appids=appids,
            imei=body.get("heybox_imei"),
            pkey=body.get("heybox_pkey"),
            sign_algo=body.get("sign_algo"),
        )
        steam_appids = steam.get_wishlist(steamid, api_key=body.get("steam_api_key"))
        diff = sync.compute_diff(heybox_items, steam_appids, name_map=name_map)
    except Exception as exc:  # noqa: BLE001
        return _error(str(exc), 502)
    return jsonify(diff)


@app.route("/api/apply", methods=["POST"])
def api_apply():
    body = _body()
    to_add = body.get("to_add") or []
    to_remove = body.get("to_remove") or []
    if not to_add and not to_remove:
        return _error("to_add or to_remove is required", 400)
    try:
        result = sync.apply_changes(
            to_add,
            to_remove,
            body.get("steam_access_token"),
            dry_run=bool(body.get("dry_run")),
        )
    except Exception as exc:  # noqa: BLE001
        return _error(str(exc), 502)
    return jsonify(result)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5091"))
    app.run(host="0.0.0.0", port=port, debug=False)
