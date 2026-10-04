"""Atomic entry point for the ESAP evolution transaction."""

from __future__ import annotations

from .evolution_transaction import EvolutionTransaction, execute_evolution_transaction
from .transaction_atomicity import AtomicTransactionResult, run_atomic_transaction
from .abort_evidence import build_abort_evidence
from .transaction_evidence import TransactionEvidenceRecord


def execute_evolution_transaction_atomic(
    *args,
    abort_context: dict | None = None,
    **kwargs,
) -> AtomicTransactionResult[EvolutionTransaction]:
    """Execute one evolution transaction with a strict atomic boundary.

    COMMITTED is returned only when the underlying transaction produced a
    structurally valid, self-authenticating audit record. Any exception or
    malformed committed result becomes ABORTED and never exposes a partial
    transaction value.
    """
    result = run_atomic_transaction(
        lambda: execute_evolution_transaction(*args, **kwargs),
        stage="evolution-transaction",
    )
    if result.abort is None:
        value = result.value
        if value is None:
            raise RuntimeError("atomic-transaction-missing-committed-value")
        audit = getattr(value, "audit_record", None)
        if not isinstance(audit, TransactionEvidenceRecord):
            raise RuntimeError("atomic-transaction-missing-audit-record")
        if not audit.verify_digest():
            raise RuntimeError("atomic-transaction-invalid-audit-digest")
        return result

    context = abort_context or {}
    evidence = build_abort_evidence(
        transaction_id=context.get("transaction_id", "atomic-abort"),
        source_architecture_id=context.get("source_architecture_id", "unknown-source"),
        candidate_architecture_id=context.get("candidate_architecture_id", "unknown-candidate"),
        stage=result.abort.stage,
        reason=result.abort.reason,
        attempted_mutations=tuple(context.get("attempted_mutations", ())),
        verification_evidence=tuple(context.get("verification_evidence", ())),
        residuals=tuple(context.get("residuals", ())),
    )
    return AtomicTransactionResult(result.disposition, None, result.abort, evidence)
