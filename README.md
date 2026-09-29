# Hey2Steam

Sync your **HeyBox (小黑盒)** game wishlist into your **Steam** wishlist.

Given a HeyBox user ID, Hey2Steam fetches that user's wishlist and batch-adds
the missing games to your Steam wishlist. It is available both as a command
line tool and as a web app.

> **Note on authentication.** Reading a Steam wishlist only needs a public
> SteamID. *Writing* to a Steam wishlist is **not** covered by the Web API key
> — Steam requires a user access token (`webapi_token`). See
> [Credentials](#credentials) below.

## Features

- Fetches a HeyBox wishlist (with automatic request signing).
- Reads the current Steam wishlist and computes the diff.
- Adds missing games to Steam (access-token method, with a legacy session fallback).
- `--dry-run` mode to preview the diff without writing anything.
- Command line tool + Flask web app + static GitHub Pages page.
- Bilingual web UI (English / 中文) with a language switch.
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
python main.py --heybox-id 12345678 --steam-id 7656119xxxxxxxxxx \
    --steam-access-token <webapi_token> --dry-run
```

Remove `--dry-run` to actually write to Steam. Run `python main.py --help`
for all options. Any option can instead be provided via a `.env` file (copy
`.env.example` to `.env`) or an environment variable.

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
| Access token (`webapi_token`) | Log into Steam, open `store.steampowered.com/pointssummary/ajaxgetasyncconfig`, copy `webapi_token` | **Writing** (required) |
| Steam API key | `steamcommunity.com/dev/apikey` | Reading (optional) |

The access token expires roughly every 24 hours and must be refreshed.

## How it works

1. **Fetch** — request the HeyBox `get_game_list_v3` endpoint with
   `sort_type=heybox_wish` and a valid `hkey` signature.
2. **Compare** — read the current Steam wishlist via
   `IWishlistService/GetWishlist` and compute the missing appids.
3. **Sync** — add each missing appid via `IWishlistService/AddToWishlist`
   (or the legacy store endpoint as a fallback).

## Project structure

```
Hey2Steam/
├── hey2steam/
│   ├── __init__.py
│   ├── config.py      # env / .env loading (no hardcoded secrets)
│   ├── errors.py      # exception types
│   ├── signing.py     # HeyBox hkey signature (web + chat variants)
│   ├── heybox.py      # HeyBox wishlist client
│   ├── steam.py       # Steam wishlist read + write
│   └── sync.py        # orchestration
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
