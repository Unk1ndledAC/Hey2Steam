#!/usr/bin/env python3
"""Fetch the full Steam app list and write it to ``data/steam_games.json``.

Used by the daily GitHub Actions workflow (``.github/workflows/``). Requires a
Steam Web API key, provided as the first CLI argument or via the
``STEAM_API_KEY`` environment variable.

Usage:
    python scripts/update_game_list.py
    python scripts/update_game_list.py <api_key>
"""

import json
import os
import sys
from pathlib import Path

# Allow running directly from the repo root without installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hey2steam import steam  # noqa: E402


def main():
    api_key = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("STEAM_API_KEY")
    if not api_key:
        print("error: STEAM_API_KEY is required (env var or first argument)", file=sys.stderr)
        return 1

    print("Fetching the Steam app list...")
    apps = steam.get_app_list(api_key)

    out_dir = Path(__file__).resolve().parent.parent / "data"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "steam_games.json"
    payload = {"total": len(apps), "apps": apps}
    out_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(apps)} apps to {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
