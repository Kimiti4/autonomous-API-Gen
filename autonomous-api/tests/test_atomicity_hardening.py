import pytest

from app.engine.abort_evidence import build_abort_evidence
from app.engine.atomic_evolution_transaction import execute_evolution_transaction_atomic
from app.engine.transaction_atomicity import TransactionDisposition
from app.engine.transaction_evidence import TransactionEvidenceRecord
from app.engine.trust_boundary import TrustContext


def test_atomic_commit_requires_authenticated_audit(monkeypatch):
    import app.engine.atomic_evolution_transaction as module

    class Result:
        audit_record = None

    monkeypatch.setattr(module, "execute_evolution_transaction", lambda *a, **k: Result())
    with pytest.raises(RuntimeError, match="missing-audit-record"):
        module.execute_evolution_transaction_atomic(
            abort_context={"transaction_id":"tx-audit","source_architecture_id":"src","candidate_architecture_id":"cand"},
            trust_context=TrustContext("esap","tx-audit","src","cand"),
        )


def test_atomic_commit_rejects_tampered_audit(monkeypatch):
    import app.engine.atomic_evolution_transaction as module

    class Result:
        audit_record = build_abort_evidence(
            transaction_id="wrong-kind",
            source_architecture_id="src",
            candidate_architecture_id="cand",
            stage="test",
            reason="test",
        )

    monkeypatch.setattr(module, "execute_evolution_transaction", lambda *a, **k: Result())
    with pytest.raises(RuntimeError, match="missing-audit-record"):
        module.execute_evolution_transaction_atomic()


def test_atomic_abort_is_explicit_and_has_no_partial_value(monkeypatch):
    import app.engine.atomic_evolution_transaction as module

    monkeypatch.setattr(
        module,
        "execute_evolution_transaction",
        lambda *a, **k: (_ for _ in ()).throw(ValueError("verification failed")),
    )
    result = module.execute_evolution_transaction_atomic(
        abort_context={
            "transaction_id": "tx-hard",
            "source_architecture_id": "src",
            "candidate_architecture_id": "cand",
        }
    )
    assert result.disposition is TransactionDisposition.ABORTED
    assert result.value is None
    assert result.evidence is not None


def test_abort_unification_preserves_parent_digest():
    abort = build_abort_evidence(
        transaction_id="tx-child",
        source_architecture_id="src",
        candidate_architecture_id="cand",
        stage="verification",
        reason="failed",
    )
    record = TransactionEvidenceRecord.from_abort_record(abort, parent_digest="a" * 64)
    assert record.parent_digest == "a" * 64
    assert record.verify_digest()
