"""Atomic entry point for the ESAP evolution transaction."""
from __future__ import annotations

from .evolution_transaction import EvolutionTransaction, execute_evolution_transaction
from .transaction_atomicity import AtomicTransactionResult, run_atomic_transaction
from .abort_evidence import build_abort_evidence


def execute_evolution_transaction_atomic(*args, abort_context: dict | None = None, **kwargs) -> AtomicTransactionResult[EvolutionTransaction]:
    """Run the existing evolution transaction with explicit COMMITTED/ABORTED semantics.

    The underlying transaction remains responsible for its full evidence/audit
    construction. An exception at any stage produces an ABORTED result and no
    partially constructed EvolutionTransaction is returned.
    """
    result = run_atomic_transaction(
        lambda: execute_evolution_transaction(*args, **kwargs),
        stage="evolution-transaction",
    )
    if result.abort is None:
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
