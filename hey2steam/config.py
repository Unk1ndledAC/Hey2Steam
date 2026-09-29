"""Configuration loading.

All secrets are read from environment variables and an optional local
``.env`` file located at the project root. Nothing is hardcoded, so the
repository can be shared safely. The ``.env`` file itself is git-ignored.
"""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_dotenv(path=None):
    """Parse a simple ``KEY=VALUE`` ``.env`` file into ``os.environ``.

    Existing environment variables take precedence (they are never
    overwritten). Lines beginning with ``#`` are treated as comments.
    """
    path = Path(path) if path else PROJECT_ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("\"'")
        os.environ.setdefault(key, value)


def get(name, default=None):
    """Return the value of an environment variable, or ``default``."""
    return os.environ.get(name, default)
