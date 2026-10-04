from app.engine.atomic_evolution_transaction import execute_evolution_transaction_atomic
from app.engine.transaction_atomicity import TransactionDisposition


def test_atomic_abort_contains_durable_evidence(monkeypatch):
    import app.engine.atomic_evolution_transaction as module

    def fail(*args, **kwargs):
        raise ValueError("verification failed")

    monkeypatch.setattr(module, "execute_evolution_transaction", fail)
    result = module.execute_evolution_transaction_atomic(
        abort_context={
            "transaction_id": "tx-2",
            "source_architecture_id": "src-2",
            "candidate_architecture_id": "cand-2",
            "attempted_mutations": ("backend-fix",),
            "verification_evidence": ("ev-2",),
            "residuals": ("verification-failed",),
        }
    )
    assert result.disposition is TransactionDisposition.ABORTED
    assert result.value is None
    assert result.evidence is not None
    assert result.evidence.successor_admitted is False
    assert result.evidence.transaction_id == "tx-2"
    assert len(result.evidence.evidence_digest()) == 64
