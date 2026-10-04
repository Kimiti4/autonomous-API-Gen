import pytest

from app.engine.abort_evidence import build_abort_evidence
from app.engine.atomic_evolution_transaction import execute_evolution_transaction_atomic
from app.engine.transaction_atomicity import TransactionDisposition
from app.engine.transaction_evidence import TransactionEvidenceRecord
from app.engine.transaction_isolation import TransactionIsolationRegistry
from app.engine.trust_boundary import TrustContext, TrustBoundaryViolation


def valid_record():
    return TransactionEvidenceRecord.from_abort_record(
        build_abort_evidence(
            transaction_id="tx",
            source_architecture_id="source",
            candidate_architecture_id="candidate",
            stage="test",
            reason="valid",
        )
    )


def test_atomic_entry_enforces_trust_before_execution(monkeypatch):
    import app.engine.atomic_evolution_transaction as module
    called = {"value": False}

    def execute(*args, **kwargs):
        called["value"] = True
        class Result:
            audit_record = valid_record()
        return Result()

    monkeypatch.setattr(module, "execute_evolution_transaction", execute)
    result = execute_evolution_transaction_atomic(
        abort_context={
            "transaction_id": "tx",
            "source_architecture_id": "source",
            "candidate_architecture_id": "candidate",
        },
        trust_context=TrustContext("", "tx", "source", "candidate"),
    )
    assert result.disposition is TransactionDisposition.ABORTED
    assert not called["value"]


def test_atomic_entry_enforces_isolation_before_execution(monkeypatch):
    import app.engine.atomic_evolution_transaction as module
    registry = TransactionIsolationRegistry()
    with registry.exclusive(
        module.transaction_isolation.transaction_lock_key("source", "candidate")
    ):
        called = {"value": False}

        def execute(*args, **kwargs):
            called["value"] = True
            class Result:
                audit_record = valid_record()
            return Result()

        monkeypatch.setattr(module, "execute_evolution_transaction", execute)
        result = execute_evolution_transaction_atomic(
            abort_context={
                "transaction_id": "tx",
                "source_architecture_id": "source",
                "candidate_architecture_id": "candidate",
            },
            trust_context=TrustContext("esap", "tx", "source", "candidate"),
            isolation_registry=registry,
        )
        assert result.disposition is TransactionDisposition.ABORTED
        assert not called["value"]


def test_atomic_entry_commits_after_trust_and_isolation(monkeypatch):
    import app.engine.atomic_evolution_transaction as module
    registry = TransactionIsolationRegistry()

    class Result:
        audit_record = valid_record()

    monkeypatch.setattr(module, "execute_evolution_transaction", lambda *a, **k: Result())
    result = execute_evolution_transaction_atomic(
        abort_context={
            "transaction_id": "tx",
            "source_architecture_id": "source",
            "candidate_architecture_id": "candidate",
        },
        trust_context=TrustContext("esap", "tx", "source", "candidate"),
        isolation_registry=registry,
    )
    assert result.disposition is TransactionDisposition.COMMITTED
    assert result.value is not None


def test_isolation_failure_generates_abort_evidence():
    import app.engine.atomic_evolution_transaction as module
    registry = TransactionIsolationRegistry()
    with registry.exclusive(
        module.transaction_isolation.transaction_lock_key("source", "candidate")
    ):
        result = execute_evolution_transaction_atomic(
            abort_context={
                "transaction_id": "tx-conflict",
                "source_architecture_id": "source",
                "candidate_architecture_id": "candidate",
            },
            isolation_registry=registry,
        )
    assert result.disposition is TransactionDisposition.ABORTED
    assert result.value is None
    assert result.evidence is not None
    assert "transaction-conflict" in result.abort.reason
