"""Explicit commit/abort semantics for ESAP evolution transactions."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Generic, TypeVar

T = TypeVar("T")


class TransactionDisposition(str, Enum):
    COMMITTED = "COMMITTED"
    ABORTED = "ABORTED"


@dataclass(frozen=True)
class TransactionAbort:
    stage: str
    reason: str


@dataclass(frozen=True)
class AtomicTransactionResult(Generic[T]):
    disposition: TransactionDisposition
    value: T | None
    abort: TransactionAbort | None
    evidence: object | None = None


def run_atomic_transaction(
    operation: Callable[[], T],
    *,
    stage: str = "transaction",
) -> AtomicTransactionResult[T]:
    try:
        value = operation()
    except Exception as exc:
        return AtomicTransactionResult(
            TransactionDisposition.ABORTED,
            None,
            TransactionAbort(stage, f"{type(exc).__name__}:{exc}"),
        )
    return AtomicTransactionResult(TransactionDisposition.COMMITTED, value, None)
