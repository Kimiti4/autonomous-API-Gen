"""Explicit transaction isolation boundary for ESAP evolution transactions.

Isolation is process-local and keyed by source/candidate architecture identity.
It is deliberately fail-closed: a live exclusive lock cannot be acquired twice.
"""
from __future__ import annotations
from contextlib import contextmanager
from threading import RLock
from typing import Iterator

class TransactionIsolationError(RuntimeError):
    """Raised when transaction isolation cannot be acquired."""

# Backward-compatible canonical name retained for callers that used the
# earlier implementation-specific exception.
TransactionIsolationConflict = TransactionIsolationError

def transaction_lock_key(source_architecture_id: str, candidate_architecture_id: str) -> str:
    if not source_architecture_id or not candidate_architecture_id:
        if not source_architecture_id:
            raise ValueError("missing-source-architecture-id")
        raise ValueError("missing-candidate-architecture-id")
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


@contextmanager
def isolated_transaction(
    source_architecture_id: str,
    candidate_architecture_id: str,
    *,
    registry: TransactionIsolationRegistry | None = None,
) -> Iterator[None]:
    """Acquire the canonical isolation boundary for one source/candidate pair."""
    active_registry = registry or TransactionIsolationRegistry()
    key = transaction_lock_key(source_architecture_id, candidate_architecture_id)
    with active_registry.exclusive(key):
        yield
