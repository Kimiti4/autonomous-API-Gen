import threading

import pytest

from app.engine.transaction_isolation import (
    TransactionIsolationError,
    TransactionIsolationRegistry,
    isolated_transaction,
    transaction_lock_key,
)


def test_same_source_candidate_conflicts():
    registry = TransactionIsolationRegistry()
    key = transaction_lock_key("source", "candidate")
    with registry.exclusive(key):
        with pytest.raises(TransactionIsolationError, match="transaction-conflict"):
            with registry.exclusive(key):
                pass


def test_different_candidates_can_progress_independently():
    registry = TransactionIsolationRegistry()
    with registry.exclusive(transaction_lock_key("source", "candidate-a")):
        with registry.exclusive(transaction_lock_key("source", "candidate-b")):
            pass


def test_lock_is_released_after_scope():
    registry = TransactionIsolationRegistry()
    key = transaction_lock_key("source", "candidate")
    with registry.exclusive(key):
        pass
    with registry.exclusive(key):
        pass


def test_invalid_identity_fails_before_locking():
    with pytest.raises(ValueError, match="missing-source-architecture-id"):
        transaction_lock_key("", "candidate")
    with pytest.raises(ValueError, match="missing-candidate-architecture-id"):
        transaction_lock_key("source", "")


def test_context_manager_uses_isolation_registry():
    registry = TransactionIsolationRegistry()
    with isolated_transaction("source", "candidate", registry=registry):
        with pytest.raises(TransactionIsolationError):
            with isolated_transaction("source", "candidate", registry=registry):
                pass


def test_concurrent_conflict_is_deterministic():
    registry = TransactionIsolationRegistry()
    key = transaction_lock_key("source", "candidate")
    entered = threading.Event()
    release = threading.Event()
    outcomes = []

    def holder():
        with registry.exclusive(key):
            entered.set()
            release.wait(timeout=2)

    thread = threading.Thread(target=holder)
    thread.start()
    assert entered.wait(timeout=2)

    with pytest.raises(TransactionIsolationError):
        with registry.exclusive(key):
            pass

    release.set()
    thread.join(timeout=2)
    assert not thread.is_alive()
