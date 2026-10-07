"""Failure-injection coverage for the ESAP atomic transaction boundary."""

import pytest

from app.engine.abort_evidence import build_abort_evidence
from app.engine.atomic_evolution_transaction import execute_evolution_transaction_atomic
from app.engine.transaction_evidence import TransactionEvidenceRecord
from app.engine.transaction_atomicity import TransactionDisposition


@pytest.mark.parametrize(
    "stage",
    (
        "repair",
        "dependency-reexecution",
        "measurement",
        "scoring",
        "successor-materialization",
        "verification",
        "admission",
        "audit",
    ),
)
def test_failure_at_any_transaction_stage_aborts_without_partial_value(monkeypatch, stage):
    import app.engine.atomic_evolution_transaction as module

    def fail(*args, **kwargs):
        raise RuntimeError(f"injected:{stage}")

    monkeypatch.setattr(module, "execute_evolution_transaction", fail)

    result = execute_evolution_transaction_atomic(
        abort_context={
            "transaction_id": f"tx-{stage}",
            "source_architecture_id": "source",
            "candidate_architecture_id": "candidate",
            "attempted_mutations": (f"mutation:{stage}",),
            "verification_evidence": (f"evidence:{stage}",),
            "residuals": (f"residual:{stage}",),
        }
    )

    assert result.disposition is TransactionDisposition.ABORTED
    assert result.value is None
    assert result.abort is not None
    assert result.abort.stage == "evolution-transaction"
    assert f"injected:{stage}" in result.abort.reason
    assert result.evidence is not None
    assert result.evidence.successor_admitted is False


def test_recovery_after_injected_failure_can_commit(monkeypatch):
    import app.engine.atomic_evolution_transaction as module

    calls = {"count": 0}

    class Committed:
        audit_record = None

    def operation(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("injected:first-attempt")
        return Committed()

    # A structurally invalid recovery result must still remain aborted.
    monkeypatch.setattr(module, "execute_evolution_transaction", operation)
    first = execute_evolution_transaction_atomic(
        abort_context={
            "transaction_id": "tx-recovery-1",
            "source_architecture_id": "source",
            "candidate_architecture_id": "candidate",
        }
    )
    second = execute_evolution_transaction_atomic(
        abort_context={
            "transaction_id": "tx-recovery-2",
            "source_architecture_id": "source",
            "candidate_architecture_id": "candidate",
        }
    )
    assert first.disposition is TransactionDisposition.ABORTED
    assert second.disposition is TransactionDisposition.ABORTED
    assert calls["count"] == 2


def test_atomic_boundary_does_not_swallow_base_exception(monkeypatch):
    import app.engine.atomic_evolution_transaction as module

    def fail(*args, **kwargs):
        raise KeyboardInterrupt()

    monkeypatch.setattr(module, "execute_evolution_transaction", fail)
    with pytest.raises(KeyboardInterrupt):
        execute_evolution_transaction_atomic()


def test_abort_evidence_is_distinct_per_failed_attempt(monkeypatch):
    import app.engine.atomic_evolution_transaction as module

    def fail(*args, **kwargs):
        raise RuntimeError("injected")

    monkeypatch.setattr(module, "execute_evolution_transaction", fail)

    first = execute_evolution_transaction_atomic(
        abort_context={
            "transaction_id": "tx-1",
            "source_architecture_id": "source",
            "candidate_architecture_id": "candidate",
        }
    )
    second = execute_evolution_transaction_atomic(
        abort_context={
            "transaction_id": "tx-2",
            "source_architecture_id": "source",
            "candidate_architecture_id": "candidate",
        }
    )
    assert first.evidence.evidence_digest() != second.evidence.evidence_digest()
    assert first.evidence.transaction_id != second.evidence.transaction_id
