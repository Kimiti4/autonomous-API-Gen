"""Phase 28 - Governance exception registry.

GovernanceExceptionISR records are immutable once granted; revocation is
tracked as a separate audit fact so the historical record is never rewritten.
"""

from __future__ import annotations

from datetime import datetime

from .schemas import GovernanceExceptionISR


class ExceptionRegistry:
    def __init__(self) -> None:
        self._exceptions: dict[str, GovernanceExceptionISR] = {}
        self._revocations: dict[str, tuple[str, datetime]] = {}  # id -> (actor, at)

    def register(self, exception: GovernanceExceptionISR) -> None:
        if exception.exception_id in self._exceptions:
            raise ValueError(f"duplicate_exception_id:{exception.exception_id}")
        self._exceptions[exception.exception_id] = exception

    def revoke(self, exception_id: str, *, actor: str, now: datetime) -> None:
        if exception_id not in self._exceptions:
            raise KeyError(f"unknown_exception_id:{exception_id}")
        if exception_id in self._revocations:
            raise ValueError(f"already_revoked:{exception_id}")
        self._revocations[exception_id] = (actor, now)

    def active(self, now: datetime) -> tuple[GovernanceExceptionISR, ...]:
        """Not revoked, not expired, ordered by grant time."""
        result = [
            exc for exc in self._exceptions.values()
            if exc.exception_id not in self._revocations
            and (exc.expires_at is None or exc.expires_at > now)
        ]
        return tuple(sorted(result, key=lambda e: e.granted_at))

    def all(self) -> tuple[GovernanceExceptionISR, ...]:
        return tuple(self._exceptions.values())
