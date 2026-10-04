from app.engine.transaction_atomicity import (
    TransactionDisposition, run_atomic_transaction,
)


def test_success_commits():
    result = run_atomic_transaction(lambda: "success", stage="admission")
    assert result.disposition is TransactionDisposition.COMMITTED
    assert result.value == "success"
    assert result.abort is None


def test_failure_aborts_without_partial_value():
    result = run_atomic_transaction(
        lambda: (_ for _ in ()).throw(RuntimeError("verification failed")),
        stage="verification",
    )
    assert result.disposition is TransactionDisposition.ABORTED
    assert result.value is None
    assert result.abort.stage == "verification"
    assert "verification failed" in result.abort.reason
