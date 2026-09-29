"""Exception types used across Hey2Steam."""


class Hey2SteamError(Exception):
    """Base class for all Hey2Steam errors."""


class ConfigError(Hey2SteamError):
    """Raised when required configuration or credentials are missing."""


class HeyBoxError(Hey2SteamError):
    """Raised when the HeyBox API request fails or returns an unexpected body."""


class SteamError(Hey2SteamError):
    """Raised when the Steam API request fails or returns an unexpected body."""
