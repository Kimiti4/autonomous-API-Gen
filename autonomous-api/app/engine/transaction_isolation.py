"""Concurrency and isolation controls for ESAP transaction execution."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from threading import RLock
from typing import Iterator


class TransactionIsolationError(RuntimeError):
    """Raised when a transaction cannot acquire its required isolation lock."""


@dataclass(frozen=True)
class TransactionLockKey:
    source_architecture_id: str
    candidate_architecture_id: str

    def __post_init__(self) -> None:
        if not self.source_architecture_id:
            raise ValueError("missing-source-architecture-id")
        if not self.candidate_architecture_id:
            raise ValueError("missing-candidate-architecture-id")


class TransactionIsolationRegistry:
    """Process-local, fail-closed registry for exclusive transaction scopes."""

    def __init__(self) -> None:
        self._guard = RLock()
        self._locks: dict[TransactionLockKey, RLock] = {}

    def _lock_for(self, key: TransactionLockKey) -> RLock:
        with self._guard:
            return self._locks.setdefault(key, RLock())

    @contextmanager
    def exclusive(self, key: TransactionLockKey) -> Iterator[None]:
        lock = self._lock_for(key)
        acquired = lock.acquire(blocking=False)
        if not acquired:
            raise TransactionIsolationError(
                f"transaction-conflict:{key.source_architecture_id}:{key.candidate_architecture_id}"
            )
        try:
            yield
        finally:
            lock.release()


_default_registry = TransactionIsolationRegistry()


def transaction_lock_key(source_architecture_id: str, candidate_architecture_id: str) -> TransactionLockKey:
    return TransactionLockKey(source_architecture_id, candidate_architecture_id)


@contextmanager
def isolated_transaction(
    source_architecture_id: str,
    candidate_architecture_id: str,
    *,
    registry: TransactionIsolationRegistry | None = None,
) -> Iterator[None]:
    """Acquire an exclusive transaction scope; conflict fails before mutation."""
    key = transaction_lock_key(source_architecture_id, candidate_architecture_id)
    with (registry or _default_registry).exclusive(key):
        yield
