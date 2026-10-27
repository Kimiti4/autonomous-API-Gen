"""Independently authored runtime checks for the W12 executable effect contract.

This module is not collected by the workspace suite (its filename is not a test
pattern). The generated-backend integration test copies it into a compiled
repository as ``tests/test_effect_contract.py`` and runs it there, so the
expectations are written against the declared contract rather than derived from
the emitter.
"""
from __future__ import annotations

import threading

import pytest

from app.application.Payments import PaymentsService
from app.core.behavior import BehaviorError
from app.effects.RecordPayment import apply

CLERK = {"role": "clerk"}
AUDITOR = {"role": "auditor"}
EFFECT_ID = "effect:record-payment"


def test_authorized_execution_commits_once():
    ledger: dict = {}
    calls: list[str] = []

    result = apply(
        lambda: calls.append("run") or {"approved": True},
        "key-1", ledger, {"amount": 10}, CLERK,
    )

    assert result == {"approved": True}
    assert calls == ["run"]
    assert ledger == {"record_payment:key-1": {"approved": True}}


def test_replay_returns_the_recorded_result_without_reexecution():
    ledger: dict = {}
    calls: list[str] = []
    apply(lambda: calls.append("run") or {"approved": True}, "key-1", ledger, {"amount": 10}, CLERK)

    replay = apply(
        lambda: calls.append("replay") or {"approved": True},
        "key-1", ledger, {"amount": 10}, CLERK,
    )

    assert replay == {"approved": True}
    assert calls == ["run"]


def test_replay_returns_the_committed_result_even_if_the_precondition_would_now_fail():
    ledger: dict = {}
    first = apply(lambda: {"approved": True}, "key-1", ledger, {"amount": 10}, CLERK)

    replay = apply(lambda: {"approved": True}, "key-1", ledger, {"amount": 0}, CLERK)

    assert replay == first


def test_concurrent_same_key_requests_execute_once():
    ledger: dict = {}
    runs: list[str] = []
    results: list[object] = []
    barrier = threading.Barrier(8)

    def worker() -> None:
        barrier.wait()
        results.append(apply(
            lambda: runs.append("run") or {"approved": True},
            "shared-key", ledger, {"amount": 5}, CLERK,
        ))

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert results == [{"approved": True}] * 8
    assert runs == ["run"]


def test_unauthorized_role_is_denied_without_execution_or_commit():
    ledger: dict = {}
    calls: list[str] = []

    with pytest.raises(BehaviorError, match="not authorized"):
        apply(
            lambda: calls.append("run") or {"approved": True},
            "key-1", ledger, {"amount": 10}, AUDITOR,
        )

    assert calls == []
    assert ledger == {}


def test_missing_principal_is_rejected():
    with pytest.raises(BehaviorError, match="principal required"):
        apply(lambda: {"approved": True}, "key-1", {}, {"amount": 1}, None)


def test_missing_context_is_rejected():
    with pytest.raises(BehaviorError, match="context required"):
        apply(lambda: {"approved": True}, "key-1", {}, None, CLERK)


def test_precondition_failure_is_rejected_without_execution_or_commit():
    ledger: dict = {}
    calls: list[str] = []

    with pytest.raises(BehaviorError, match="precondition rejected"):
        apply(
            lambda: calls.append("run") or {"approved": True},
            "key-1", ledger, {"amount": 0}, CLERK,
        )

    assert calls == []
    assert ledger == {}


def test_postcondition_failure_is_rejected_without_commit_and_retry_re_executes():
    ledger: dict = {}
    calls: list[str] = []

    with pytest.raises(BehaviorError, match="postcondition rejected"):
        apply(
            lambda: calls.append("run") or {"approved": False},
            "key-1", ledger, {"amount": 1}, CLERK,
        )
    assert ledger == {}

    retry = apply(
        lambda: calls.append("retry") or {"approved": True},
        "key-1", ledger, {"amount": 1}, CLERK,
    )

    assert retry == {"approved": True}
    assert calls == ["run", "retry"]


def test_missing_idempotency_key_is_rejected_before_execution():
    calls: list[str] = []

    with pytest.raises(BehaviorError, match="idempotency key required"):
        apply(
            lambda: calls.append("run") or {"approved": True},
            None, {}, {"amount": 1}, CLERK,
        )

    assert calls == []


def test_service_method_enforces_the_same_contract():
    ledger: dict = {}
    service = PaymentsService()

    result = service.execute_effect(
        EFFECT_ID, "service-key", lambda: {"approved": True}, ledger,
        {"amount": 3}, CLERK,
    )

    assert result == {"approved": True}
    assert ledger == {"record_payment:service-key": {"approved": True}}

    with pytest.raises(BehaviorError, match="not authorized"):
        service.execute_effect(
            EFFECT_ID, "other-key", lambda: {"approved": True}, {},
            {"amount": 3}, AUDITOR,
        )
