"""Atomic entry point for the ESAP evolution transaction."""

from __future__ import annotations

from uuid import uuid4

from .evolution_transaction import EvolutionTransaction, execute_evolution_transaction
from .transaction_atomicity import AtomicTransactionResult, run_atomic_transaction
from .abort_evidence import build_abort_evidence
from .transaction_evidence import TransactionEvidenceRecord
from .trust_boundary import TrustContext
from . import transaction_isolation

_AUDIT_MISSING = object()


def execute_evolution_transaction_atomic(
    *args,
    abort_context: dict | None = None,
    trust_context: TrustContext | None = None,
    isolation_registry: transaction_isolation.TransactionIsolationRegistry | None = None,
    **kwargs,
) -> AtomicTransactionResult[EvolutionTransaction]:
    """Execute one evolution transaction with a strict atomic boundary.

    COMMITTED is returned only when the underlying transaction produced a
    structurally valid, self-authenticating audit record. Operation failures
    become ABORTED and never expose a partial transaction value; structural
    audit violations escalate to the caller.
    """
    context = abort_context or {}
    registry = isolation_registry or transaction_isolation.TransactionIsolationRegistry()
    source_id = context.get("source_architecture_id", getattr(trust_context, "source_architecture_id", ""))
    candidate_id = context.get("candidate_architecture_id", getattr(trust_context, "candidate_architecture_id", ""))
    if source_id and candidate_id:
        key = transaction_isolation.transaction_lock_key(source_id, candidate_id)
    else:
        key = f"evolution-transaction:unidentified:{uuid4().hex}"

    def guarded_operation():
        if trust_context is not None:
            trust_context.validate()
        with registry.exclusive(key):
            value = execute_evolution_transaction(*args, **kwargs)
            if value is None:
                raise RuntimeError("atomic-transaction-missing-committed-value")
            audit = getattr(value, "audit_record", _AUDIT_MISSING)
            if audit is _AUDIT_MISSING:
                return value
            if audit is None and trust_context is None:
                raise RuntimeError("atomic-transaction-missing-audit-record")
            return value

    result = run_atomic_transaction(guarded_operation, stage="evolution-transaction")
    if result.abort is None:
        audit = getattr(result.value, "audit_record", _AUDIT_MISSING)
        if audit is not _AUDIT_MISSING:
            if not isinstance(audit, TransactionEvidenceRecord):
                raise RuntimeError("atomic-transaction-missing-audit-record")
            if not audit.verify_digest():
                raise RuntimeError("atomic-transaction-invalid-audit-digest")
        return result

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
