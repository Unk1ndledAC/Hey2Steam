"""Hey2Steam — sync your HeyBox wishlist into your Steam wishlist.

This package exposes a small, dependency-light client for two undocumented
APIs:

* ``heybox`` — fetches a user's HeyBox (xiaohiehe) game wishlist.
* ``steam``  — reads and writes a user's Steam wishlist.

Credentials are never hardcoded; they are supplied as arguments or read from
environment variables (see :mod:`hey2steam.config`).
"""

from . import config

__version__ = "1.0.0"

# Load a local ``.env`` file (if present) so credentials are picked up
# automatically without being committed to the repository.
config.load_dotenv()

__all__ = ["config", "errors", "signing", "heybox", "steam", "sync", "__version__"]
