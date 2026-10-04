from app.engine.atomic_evolution_transaction import execute_evolution_transaction_atomic
from app.engine.transaction_atomicity import TransactionDisposition


def test_atomic_entrypoint_commits_successful_transaction(monkeypatch):
    import app.engine.atomic_evolution_transaction as module

    sentinel = object()
    monkeypatch.setattr(module, "execute_evolution_transaction", lambda *a, **k: sentinel)
    result = module.execute_evolution_transaction_atomic()
    assert result.disposition is TransactionDisposition.COMMITTED
    assert result.value is sentinel


def test_atomic_entrypoint_aborts_and_exposes_stage(monkeypatch):
    import app.engine.atomic_evolution_transaction as module

    def fail(*a, **k):
        raise ValueError("transaction-missing-verification-config")

    monkeypatch.setattr(module, "execute_evolution_transaction", fail)
    result = module.execute_evolution_transaction_atomic()
    assert result.disposition is TransactionDisposition.ABORTED
    assert result.value is None
    assert result.abort.stage == "evolution-transaction"
    assert "transaction-missing-verification-config" in result.abort.reason
