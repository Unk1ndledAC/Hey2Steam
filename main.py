#!/usr/bin/env python3
"""Hey2Steam command-line interface.

Sync a HeyBox (xiaohiehe) wishlist into a Steam wishlist.

Credentials can be provided as flags or via environment variables / a local
``.env`` file (see ``.env.example``). Nothing is hardcoded.

Examples:
    python main.py --heybox-id 123456 --steam-id 7656119xxxxxxxxxx \\
        --steam-access-token <webapi_token> --dry-run

    python main.py --heybox-id 123456 --steam-id 7656119xxxxxxxxxx
"""

import argparse
import os
import sys

from hey2steam import config, sync


def _env_or(name, flag_value):
    return flag_value if flag_value else config.get(name)


def build_parser():
    parser = argparse.ArgumentParser(
        description="Sync a HeyBox wishlist into a Steam wishlist.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--heybox-id", help="HeyBox user ID (or HEYBOX_ID)")
    parser.add_argument("--heybox-imei", help="HeyBox device id (or HEYBOX_IMEI)")
    parser.add_argument("--heybox-pkey", help="HeyBox login credential (or HEYBOX_PKEY)")
    parser.add_argument(
        "--sign-algo",
        choices=("web", "chat"),
        help="HeyBox signature variant (or HEYBOX_SIGN_ALGO)",
    )
    parser.add_argument("--steam-id", help="SteamID64 (or STEAM_ID)")
    parser.add_argument("--steam-api-key", help="Steam Web API key (or STEAM_API_KEY)")
    parser.add_argument(
        "--steam-access-token",
        help="Steam webapi_token, required to write (or STEAM_ACCESS_TOKEN)",
    )
    parser.add_argument(
        "--steam-sessionid",
        help="Legacy store sessionid fallback (or STEAM_SESSIONID)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute the diff without adding anything to Steam",
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)

    heybox_id = _env_or("HEYBOX_ID", args.heybox_id)
    steamid = _env_or("STEAM_ID", args.steam_id)

    if not heybox_id:
        print("error: HeyBox user ID is required (--heybox-id or HEYBOX_ID)", file=sys.stderr)
        return 1
    if not steamid:
        print("error: Steam ID is required (--steam-id or STEAM_ID)", file=sys.stderr)
        return 1

    access_token = _env_or("STEAM_ACCESS_TOKEN", args.steam_access_token)
    if not args.dry_run and not access_token and not args.steam_sessionid:
        print(
            "error: adding to the Steam wishlist requires an access token "
            "(--steam-access-token / STEAM_ACCESS_TOKEN) or a sessionid.",
            file=sys.stderr,
        )
        return 1

    def progress(stage, detail):
        print(f"[{stage}] {detail}")

    try:
        report = sync.sync(
            heybox_id=heybox_id,
            steamid=steamid,
            steam_access_token=access_token,
            steam_api_key=_env_or("STEAM_API_KEY", args.steam_api_key),
            steam_sessionid=_env_or("STEAM_SESSIONID", args.steam_sessionid),
            heybox_imei=_env_or("HEYBOX_IMEI", args.heybox_imei),
            heybox_pkey=_env_or("HEYBOX_PKEY", args.heybox_pkey),
            sign_algo=_env_or("HEYBOX_SIGN_ALGO", args.sign_algo),
            dry_run=args.dry_run,
            progress=progress,
        )
    except Exception as exc:  # noqa: BLE001 — surface any failure to the user
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print()
    print("== Sync report ==")
    print(f"  HeyBox wishlist:     {report['heybox_total']} games")
    print(f"  Already on Steam:    {report['already_on_steam']}")
    print(f"  {'Would add' if args.dry_run else 'Added'}:          {len(report['added'])}")
    if report["added"]:
        for item in report["added"]:
            print(f"    - {item['name'] or item['appid']} (appid {item['appid']})")
    if report["failed"]:
        print(f"  Failed:              {len(report['failed'])}")
        for item in report["failed"]:
            print(f"    - {item['name'] or item['appid']} -> {item['error']}")
    if args.dry_run:
        print("  (dry run — nothing was written)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
