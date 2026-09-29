"""HeyBox (xiaohiehe) request signing.

The HeyBox web API rejects requests unless they carry a valid ``hkey``,
``_time`` and ``nonce`` triple. This module implements the signature
generation used by the official client.

Two variants are supported because the algorithm has changed over time:

* ``web`` (default) — the current ``api.xiaoheihe.cn`` website client,
  reverse-engineered from the site's JavaScript bundle.
* ``chat`` — an older client variant found in third-party HeyBox clients.

The two variants share the same low-level byte-mixing primitives but build
the final ``hkey`` differently. If one is rejected by the live API, switch to
the other via the ``HEYBOX_SIGN_ALGO`` environment variable or the
``--sign-algo`` CLI flag.
"""

import hashlib
import random
import time

# --------------------------------------------------------------------------
# Low-level byte transformations shared by both variants.
# --------------------------------------------------------------------------


def _vm(e):
    """Single-byte mix with optional wraparound."""
    if e & 128:
        return 255 & ((e << 1) ^ 27)
    return e << 1


def _qm(e):
    return _vm(e) ^ e


def _dollar_m(e):
    return _qm(_vm(e))


def _ym(e):
    return _dollar_m(_qm(_vm(e)))


def _gm(e):
    return _ym(e) ^ _dollar_m(e) ^ _qm(e)


def _km_full(e):
    """Four-byte round-trip transform used to derive the checksum."""
    e = list(e)
    t = [0, 0, 0, 0]
    t[0] = _gm(e[0]) ^ _ym(e[1]) ^ _dollar_m(e[2]) ^ _qm(e[3])
    t[1] = _qm(e[0]) ^ _gm(e[1]) ^ _ym(e[2]) ^ _dollar_m(e[3])
    t[2] = _dollar_m(e[0]) ^ _qm(e[1]) ^ _gm(e[2]) ^ _ym(e[3])
    t[3] = _ym(e[0]) ^ _dollar_m(e[1]) ^ _qm(e[2]) ^ _gm(e[3])
    e[0], e[1], e[2], e[3] = t
    return e


def _normalize_path(path):
    """Collapse a URL path to ``/a/b/c/`` with a single leading/trailing slash."""
    return "/" + "/".join(p for p in path.split("/") if p) + "/"


# --------------------------------------------------------------------------
# Variant: "web" (current website client).
# --------------------------------------------------------------------------

_CHARSET_WEB = "AB45STUVWZEFGJ6CH01D237IXYPQRKLMN89"


def _av(text, charset, n):
    """Map each character of ``text`` through ``charset[:n]`` by codepoint."""
    table = charset[:n]
    return "".join(table[ord(c) % len(table)] for c in text)


def _sv(text, charset):
    """Map each character of ``text`` through the full ``charset``."""
    return "".join(charset[ord(c) % len(charset)] for c in text)


def _hkey_web(path, timestamp, nonce):
    comp1 = _av(str(timestamp), _CHARSET_WEB, -2)
    comp2 = _sv(_normalize_path(path), _CHARSET_WEB)
    comp3 = _sv(nonce, _CHARSET_WEB)
    comps = (comp1, comp2, comp3)
    max_len = max(len(c) for c in comps)
    interleaved = "".join(
        c[k] for k in range(max_len) for c in comps if k < len(c)
    )
    digest = hashlib.md5(interleaved[:20].encode("utf-8")).hexdigest()
    prefix = _av(digest[:5], _CHARSET_WEB, -4)
    checksum = sum(_km_full([ord(c) for c in digest[-6:]])) % 100
    return prefix + f"{checksum:02d}"


# --------------------------------------------------------------------------
# Variant: "chat" (older third-party client).
# --------------------------------------------------------------------------

_CHARSET_CHAT = "JKMNPQRTX1234OABCDFG56789H"


def _convert_to_int(text):
    """Sum the four-way byte transform over the last four characters."""
    byte_list = [ord(c) for c in text[-4:]]
    t = [0, 0, 0, 0]
    t[0] = _gm(byte_list[0]) ^ _ym(byte_list[1]) ^ _dollar_m(byte_list[2]) ^ _qm(byte_list[3])
    t[1] = _qm(byte_list[0]) ^ _gm(byte_list[1]) ^ _ym(byte_list[2]) ^ _dollar_m(byte_list[3])
    t[2] = _dollar_m(byte_list[0]) ^ _qm(byte_list[1]) ^ _gm(byte_list[2]) ^ _ym(byte_list[3])
    t[3] = _ym(byte_list[0]) ^ _dollar_m(byte_list[1]) ^ _qm(byte_list[2]) ^ _gm(byte_list[3])
    return sum(t)


def _hkey_chat(path, timestamp, nonce):
    normalized = _normalize_path(path)
    digits = "".join(c for c in nonce + _CHARSET_CHAT if c.isdigit())
    hash_nonce = hashlib.md5(digits.encode("utf-8")).hexdigest()
    seed = str(timestamp + 1) + normalized + hash_nonce
    digest = hashlib.md5(seed.encode("utf-8")).hexdigest()
    digits_only = "".join(c for c in digest if c.isdigit())[:9].ljust(9, "0")
    numeric = int(digits_only)
    code = ""
    for _ in range(5):
        code += _CHARSET_CHAT[numeric % len(_CHARSET_CHAT)]
        numeric //= len(_CHARSET_CHAT)
    checksum = str(_convert_to_int(code) % 100).zfill(2)
    return code + checksum


# --------------------------------------------------------------------------
# Public API.
# --------------------------------------------------------------------------


def hkey(path, timestamp, nonce, algo="web"):
    """Compute the ``hkey`` for ``path`` using the requested algorithm."""
    if algo == "chat":
        return _hkey_chat(path, timestamp, nonce)
    return _hkey_web(path, timestamp, nonce)


def nonce():
    """Return a fresh uppercase MD5 nonce (as used by the HeyBox client)."""
    seed = str(int(time.time())) + str(random.random())[:18]
    return hashlib.md5(seed.encode("utf-8")).hexdigest().upper()


def create_signature(path, algo="web"):
    """Return the ``hkey`` / ``_time`` / ``nonce`` triple for a request."""
    timestamp = int(time.time())
    n = nonce()
    return {
        "hkey": hkey(path, timestamp, n, algo),
        "_time": timestamp,
        "nonce": n,
    }
