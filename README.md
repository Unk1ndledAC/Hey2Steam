# Hey2Steam

Sync your **HeyBox (小黑盒)** game wishlist into your **Steam** wishlist.

Given a HeyBox user ID, Hey2Steam recovers that user's HeyBox wishlist and
batch-adds the missing games to the corresponding Steam wishlist. It ships as
both a command line tool and a web app.

> **Note on authentication.** Reading a Steam wishlist only needs a public
> SteamID. *Writing* to a Steam wishlist requires a user **access token**
> (`webapi_token`) — the Steam Web API key is read-only and cannot modify a
> wishlist. The API key is used for reading data and for fetching the Steam
> app list (see [Credentials](#credentials)).

## How HeyBox wishlists are recovered

HeyBox does not expose a user's wishlist as a single endpoint. Instead, each
game's *follow state* is public per `heybox_id` and can be queried in bulk.
Hey2Steam therefore:

1. Obtains the full Steam app list (`IStoreService/GetAppList`).
2. Batch-queries HeyBox `/game/get_game_infos` for each appid and keeps every
   game whose `follow_state` is `"following"`.
3. Diffs that list against the current Steam wishlist and adds the missing
   appids via `IWishlistService/AddToWishlist`.

This is why the app list matters, and why the daily update workflow below
keeps a fresh copy checked into the repository.

## Features

- Recovers a HeyBox wishlist by scanning follow states (no private data needed).
- Reads the current Steam wishlist and computes the diff.
- Adds missing games to Steam using the `webapi_token` access token.
- **Bidirectional diff view** — lists games on HeyBox but not Steam, and on
  Steam but not HeyBox.
- **Selective sync** — tick individual games (or select all) to add to Steam
  or remove from Steam.
- `--dry-run` mode to preview the diff without writing anything.
- Command line tool + Flask web app + static GitHub Pages page.
- Bilingual web UI (English / 中文) with a language switch.
- Daily GitHub Actions workflow to refresh the Steam app list.
- No secrets hardcoded — everything comes from arguments, environment
  variables, or a local `.env` file.

## Installation

```bash
# use your preferred Python (3.8+)
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

## Usage

### CLI

```bash
# Preview the diff (no writes) — uses the cached app list in data/steam_games.json
python main.py --heybox-id 12345678 --steam-id 7656119xxxxxxxxxx \
    --steam-access-token <webapi_token> --dry-run

# Actually sync (drop --dry-run)
python main.py --heybox-id 12345678 --steam-id 7656119xxxxxxxxxx \
    --steam-access-token <webapi_token>
```

If `data/steam_games.json` is missing, pass `--steam-api-key <key>` to fetch
the app list live. Run `python main.py --help` for all options. Any option can
instead be provided via a `.env` file (copy `.env.example` to `.env`) or an
environment variable.

### Web app (local)

```bash
python app.py
```

Open <http://localhost:5091>. The same UI is also shipped as `docs/index.html`
and can be hosted statically (see below). When hosted statically, the page
detects that no backend is present and lets you connect to a locally running
backend via the **Backend URL** field.

### GitHub Pages (static)

`docs/index.html` is a self-contained page. To publish it alongside your blog,
copy the body of `docs/index.html` into a new Hexo source page (with front
matter), e.g. `MyBlog/source/hey2steam/index.html`:

```text
---
title: Hey2Steam
layout: false
---
<contents of docs/index.html>
```

## Credentials

| Field | Where to get it | Purpose |
|-------|-----------------|---------|
| HeyBox User ID | Your numeric ID in the HeyBox profile / API requests | Source wishlist |
| SteamID64 | `steamid.io` or your Steam profile URL | Destination wishlist |
| Access token (`webapi_token`) | Log into Steam → open `store.steampowered.com/pointssummary/ajaxgetasyncconfig` → copy `webapi_token` | **Writing** (required) |
| Steam Web API key | `steamcommunity.com/dev/apikey` | Reading + fetching the app list |

The `webapi_token` expires roughly every 24 hours and must be refreshed before
each write. The API key is permanent once created and is only used for reading
data and fetching the app list.

### Getting the Steam Web API key

1. Log into <https://steamcommunity.com/dev/apikey>.
2. Enter any domain name (e.g. `localhost` or your GitHub Pages domain) and
   agree to the terms.
3. Click **Register** and copy the 32-character key.

Your account must have made at least one purchase — Steam's "limited" accounts
cannot generate a key. There is no faster official route; this is the single
supported way to obtain a permanent key.

### Getting the `webapi_token`

1. Log into <https://store.steampowered.com>.
2. Open <https://store.steampowered.com/pointssummary/ajaxgetasyncconfig>.
3. Copy the `webapi_token` value from the JSON response.

## Daily app-list update (GitHub Actions)

`.github/workflows/update-game-list.yml` refreshes `data/steam_games.json`
once a day (00:00 UTC) and commits any changes. To enable it:

1. Add a repository secret named `STEAM_API_KEY` with your Steam Web API key
   (Settings → Secrets and variables → Actions → New repository secret).
2. The workflow also supports manual runs from the **Actions** tab.

You can run the same update locally at any time:

```bash
python scripts/update_game_list.py <api_key>
```

Note that `data/steam_games.json` holds roughly 190k entries (~several MB), so
each daily update adds a non-trivial commit; this is expected.

## Project structure

```
Hey2Steam/
├── hey2steam/
│   ├── __init__.py
│   ├── config.py      # env / .env loading (no hardcoded secrets)
│   ├── errors.py      # exception types
│   ├── signing.py     # HeyBox hkey signature (web + chat variants)
│   ├── heybox.py      # HeyBox follow-state scan (wishlist recovery)
│   ├── steam.py       # Steam wishlist read + write + app list
│   └── sync.py        # orchestration
├── scripts/
│   └── update_game_list.py   # refresh data/steam_games.json
├── .github/workflows/
│   └── update-game-list.yml  # daily scheduled refresh
├── main.py            # CLI entry point
├── app.py             # Flask web server + JSON API
├── docs/index.html    # static, bilingual web UI (also served by Flask)
├── tests/test_signing.py
├── requirements.txt
├── .env.example
└── README.md
```

## Disclaimer

This project is not affiliated with HeyBox or Valve/Steam. It relies on
unofficial APIs and reverse-engineered request signing that may change without
notice. Use it at your own risk and respect each platform's terms of service.
Credentials are only sent to the backend you configure and are never persisted.

## License

MIT — see [LICENSE](LICENSE).
