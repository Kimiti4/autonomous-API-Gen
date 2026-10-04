"""Fail-closed recovery and resume state for ESAP transactions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Generic, TypeVar

from .transaction_evidence import TransactionEvidenceRecord
from .transaction_evidence_chain import TransactionEvidenceChain

T = TypeVar("T")


class RecoveryDisposition(str, Enum):
    RESUMABLE = "RESUMABLE"
    TERMINAL = "TERMINAL"


@dataclass(frozen=True)
class TransactionRecoveryCheckpoint:
    """Durable checkpoint describing the last safe transaction boundary."""

    transaction_id: str
    stage: str
    evidence_digest: str
    disposition: RecoveryDisposition

    def __post_init__(self) -> None:
        if not self.transaction_id:
            raise ValueError("missing-transaction-id")
        if not self.stage:
            raise ValueError("missing-recovery-stage")
        if not self.evidence_digest:
            raise ValueError("missing-evidence-digest")


@dataclass(frozen=True)
class RecoveryResult(Generic[T]):
    disposition: RecoveryDisposition
    value: T | None
    checkpoint: TransactionRecoveryCheckpoint
    reason: str | None = None


def checkpoint_from_evidence(
    record: TransactionEvidenceRecord,
    *,
    stage: str,
    resumable: bool,
) -> TransactionRecoveryCheckpoint:
    if not record.verify_digest():
        raise ValueError(f"invalid-record-digest:{record.transaction_id}")
    return TransactionRecoveryCheckpoint(
        transaction_id=record.transaction_id,
        stage=stage,
        evidence_digest=record.digest,
        disposition=(
            RecoveryDisposition.RESUMABLE
            if resumable
            else RecoveryDisposition.TERMINAL
        ),
    )


def validate_checkpoint(
    checkpoint: TransactionRecoveryCheckpoint,
    chain: TransactionEvidenceChain,
) -> bool:
    """A checkpoint is usable only if its evidence is the current chain tip."""
    if not chain.verify():
        return False
    return (
        checkpoint.evidence_digest == chain.tip_digest
        and any(
            record.transaction_id == checkpoint.transaction_id
            and record.digest == checkpoint.evidence_digest
            for record in chain.records
        )
    )


def resume_from_checkpoint(
    checkpoint: TransactionRecoveryCheckpoint,
    chain: TransactionEvidenceChain,
    operation: Callable[[], T],
) -> RecoveryResult[T]:
    """Resume only from a valid resumable tip; never bypass chain integrity."""
    if checkpoint.disposition is not RecoveryDisposition.RESUMABLE:
        return RecoveryResult(
            RecoveryDisposition.TERMINAL,
            None,
            checkpoint,
            "checkpoint-not-resumable",
        )
    if not validate_checkpoint(checkpoint, chain):
        return RecoveryResult(
            RecoveryDisposition.TERMINAL,
            None,
            checkpoint,
            "checkpoint-invalid-or-not-chain-tip",
        )
    try:
        value = operation()
    except Exception as exc:
        return RecoveryResult(
            RecoveryDisposition.RESUMABLE,
            None,
            checkpoint,
            f"{type(exc).__name__}:{exc}",
        )
    return RecoveryResult(RecoveryDisposition.RESUMABLE, value, checkpoint)
