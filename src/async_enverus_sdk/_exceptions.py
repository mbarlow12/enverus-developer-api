"""Exception classes for the Enverus Developer API client."""


class DAError(Exception):
    """Base exception for all Enverus Developer API errors."""


class DAAuthException(DAError):
    """Raised when authentication fails (bad credentials, throttled token request)."""


class DAQueryException(DAError):
    """Raised when a query returns an error (400, non-200 during pagination)."""


class DADatasetException(DAError):
    """Raised when an invalid dataset name is provided (404)."""
