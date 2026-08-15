"""
Phase 28 — Governance Dashboard errors.

The dashboard fails closed: any kernel failure is surfaced as
KernelUnavailableError and rendered as a 503, never as a silent allow.
"""

from __future__ import annotations


class DashboardError(Exception):
    """Base class for dashboard errors."""

    status_code = 500
    title = "Dashboard error"

    def __init__(self, message: str = "") -> None:
        super().__init__(message or self.title)
        self.message = message or self.title


class UnauthorizedError(DashboardError):
    status_code = 401
    title = "Authentication required"


class ForbiddenError(DashboardError):
    status_code = 403
    title = "Forbidden"


class NotFoundError(DashboardError):
    status_code = 404
    title = "Not found"


class ValidationError(DashboardError):
    status_code = 422
    title = "Invalid request"


class KernelUnavailableError(DashboardError):
    """Fail-closed error: the governance kernel could not be reached."""

    status_code = 503
    title = "Governance kernel unavailable"

    def __init__(self, message: str = "", *, cause: Exception | None = None) -> None:
        super().__init__(message or "The governance kernel could not be reached.")
        self.cause = cause
