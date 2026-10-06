"""Explicit transaction isolation boundary for ESAP evolution transactions.

Isolation is process-local and keyed by source/candidate architecture identity.
It is deliberately fail-closed: a live exclusive lock cannot be acquired twice.
"""
from __future__ import annotations
from contextlib import contextmanager
from threading import RLock
from typing import Iterator

class TransactionIsolationConflict(RuntimeError):
    """Raised when another transaction owns the requested isolation key."""

def transaction_lock_key(source_architecture_id: str, candidate_architecture_id: str) -> str:
    if not source_architecture_id or not candidate_architecture_id:
        raise ValueError("transaction-isolation-requires-identities")
    return f"{source_architecture_id}->{candidate_architecture_id}"

class TransactionIsolationRegistry:
    def __init__(self) -> None:
        self._guard = RLock()
        self._locks: dict[str, bool] = {}

    @contextmanager
    def exclusive(self, key: str) -> Iterator[None]:
        if not key:
            raise ValueError("transaction-isolation-requires-key")
        with self._guard:
            if self._locks.get(key, False):
                raise TransactionIsolationConflict("transaction-conflict:" + key)
            self._locks[key] = True
        try:
            yield
        finally:
            with self._guard:
                self._locks.pop(key, None)
