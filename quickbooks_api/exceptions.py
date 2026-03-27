"""Custom exceptions for QuickBooks API client."""


class QuickBooksError(Exception):
    """Base exception for QuickBooks API errors."""

    def __init__(self, message: str, status_code: int | None = None, detail: dict | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.detail = detail or {}


class AuthenticationError(QuickBooksError):
    """Raised when authentication fails (401)."""


class AuthorizationError(QuickBooksError):
    """Raised when authorization fails (403)."""


class NotFoundError(QuickBooksError):
    """Raised when a resource is not found (404)."""


class ValidationError(QuickBooksError):
    """Raised when the request is invalid (400)."""


class RateLimitError(QuickBooksError):
    """Raised when rate limited (429)."""


class ServerError(QuickBooksError):
    """Raised when the QBO server returns 5xx."""


class StaleObjectError(QuickBooksError):
    """Raised when updating a stale object (optimistic locking)."""
