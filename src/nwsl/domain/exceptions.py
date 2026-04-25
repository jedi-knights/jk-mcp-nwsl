"""Domain exceptions for the NWSL application.

All exceptions raised by the application layer or adapters are rooted here.
Callers can catch NWSLError to handle any domain-level failure, or catch
subclasses for finer-grained handling.
"""


class NWSLError(Exception):
    """Base class for all NWSL domain exceptions."""


class NWSLNotFoundError(NWSLError):
    """Raised when the requested resource does not exist (HTTP 404)."""


class UpstreamAPIError(NWSLError):
    """Raised when the upstream ESPN API returns an unexpected error (non-2xx HTTP response)."""
