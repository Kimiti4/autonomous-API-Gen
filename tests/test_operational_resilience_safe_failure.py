"""
Tests for Phase 22.6 operational resilience and safe failure hardening.
"""

from civilization.resilience.engine import ResilienceEngine
from civilization.resilience.models import (
    CircuitBreakerConfig,
    CircuitState,
    DegradationMode,
    ResiliencePolicy,
    RetryPolicy,
)


def build_engine(
    failure_threshold: int = 3,
    cooldown_seconds: int = 60,
) -> ResilienceEngine:
    policy = ResiliencePolicy(
        default_circuit=CircuitBreakerConfig(
            failure_threshold=failure_threshold,
            success_threshold_half_open=2,
            cooldown_seconds=cooldown_seconds,
        ),
        default_retry=RetryPolicy(
            max_attempts=3,
            initial_delay_seconds=0.1,
            max_delay_seconds=1.0,
            backoff_multiplier=2.0,
            budget_window_seconds=60,
            budget_max_attempts=10,
        ),
        high_impact_fail_closed=True,
        open_circuit_degradation_threshold=5,
    )

    return ResilienceEngine(policy=policy)


def test_circuit_breaker_opens_after_failures():
    engine = build_engine(failure_threshold=3, cooldown_seconds=60)

    for _ in range(3):
        engine.record_failure(
            component="knowledge_graph_sync",
            operation="sync_memory",
            error="timeout",
        )

    circuit = engine.get_circuit("knowledge_graph_sync", "sync_memory")

    assert circuit.state.value == "OPEN"

    check = engine.allow_request(
        component="knowledge_graph_sync",
        operation="sync_memory",
        action_category="MUTATE",
    )

    assert check.allowed is False


def test_safe_stop_blocks_non_read_actions():
    engine = build_engine()

    engine.set_degradation_mode(
        mode=DegradationMode.SAFE_STOP,
        reason="Critical incident",
    )

    read_check = engine.allow_request(
        component="dashboard",
        operation="read_metrics",
        action_category="READ",
    )

    mutate_check = engine.allow_request(
        component="civilization",
        operation="run_task",
        action_category="MUTATE",
    )

    assert read_check.allowed is True
    assert mutate_check.allowed is False


def test_high_impact_fails_closed_when_degraded():
    engine = build_engine()

    engine.set_degradation_mode(
        mode=DegradationMode.DEGRADED,
        reason="Partial outage",
    )

    check = engine.allow_request(
        component="evolution",
        operation="promote_candidate",
        action_category="PROMOTE",
        high_impact=True,
    )

    assert check.allowed is False
    assert check.required_human_approval is True


def test_quorum_loss_detection():
    engine = build_engine()

    quorum = engine.evaluate_quorum(
        group_id="federation_1",
        total_weight=10.0,
        participating_weight=4.0,
        required_ratio=0.5,
    )

    assert quorum.quorum_met is False
    assert engine.mode == DegradationMode.DEGRADED


def test_retry_budget_limits():
    engine = build_engine()

    first = engine.retry_decision("sync_memory", attempt=0)
    second = engine.retry_decision("sync_memory", attempt=1)
    third = engine.retry_decision("sync_memory", attempt=2)
    fourth = engine.retry_decision("sync_memory", attempt=3)

    assert first.allowed is True
    assert second.allowed is True
    assert third.allowed is True
    assert fourth.allowed is False


def test_chaos_drill_opens_circuit():
    engine = build_engine(failure_threshold=2, cooldown_seconds=60)

    drill = engine.run_chaos_drill(
        name="knowledge_sync_failure_drill",
        scenario="sync_memory",
        target_component="knowledge_graph_sync",
        expected_safe_state="OPEN",
        failure_count=2,
    )

    assert drill.passed is True

    circuit = engine.get_circuit("knowledge_graph_sync", "sync_memory")

    assert circuit.state.value == "OPEN"


def test_circuit_recovers_after_success():
    engine = build_engine(failure_threshold=2, cooldown_seconds=0)

    for _ in range(2):
        engine.record_failure(
            component="test_service",
            operation="op",
            error="fail",
        )

    circuit = engine.get_circuit("test_service", "op")
    assert circuit.state.value == "OPEN"

    engine.record_success("test_service", "op")
    circuit = engine.get_circuit("test_service", "op")
    assert circuit.state.value == "HALF_OPEN"

    engine.record_success("test_service", "op")
    engine.record_success("test_service", "op")
    circuit = engine.get_circuit("test_service", "op")
    assert circuit.state.value == "CLOSED"


def test_read_only_blocks_non_read_actions():
    engine = build_engine()

    engine.set_degradation_mode(
        mode=DegradationMode.READ_ONLY,
        reason="Maintenance window",
    )

    read_check = engine.allow_request(
        component="dashboard",
        operation="read_metrics",
        action_category="READ",
    )

    mutate_check = engine.allow_request(
        component="civilization",
        operation="create_task",
        action_category="MUTATE",
    )

    assert read_check.allowed is True
    assert mutate_check.allowed is False
    assert mutate_check.required_human_approval is True


def test_open_circuit_blocks_during_cooldown():
    engine = build_engine(failure_threshold=1, cooldown_seconds=60)

    engine.record_failure(
        component="service",
        operation="op",
        error="fail",
    )

    circuit = engine.get_circuit("service", "op")
    assert circuit.state.value == "OPEN"

    check = engine.allow_request(
        component="service",
        operation="op",
        action_category="READ",
    )

    assert check.allowed is False


def test_retry_backoff_is_deterministic():
    engine = build_engine()

    decisions = []
    for attempt in range(4):
        decision = engine.retry_decision("test_op", attempt=attempt)
        decisions.append(decision)

    assert decisions[0].delay_seconds == 0.1
    assert decisions[1].delay_seconds == 0.2
    assert decisions[2].delay_seconds == 0.4
    assert decisions[3].allowed is False


def test_quorum_met_keeps_normal_mode():
    engine = build_engine()

    quorum = engine.evaluate_quorum(
        group_id="federation_1",
        total_weight=10.0,
        participating_weight=8.0,
        required_ratio=0.5,
    )

    assert quorum.quorum_met is True
    assert engine.mode == DegradationMode.NORMAL


def test_kill_switch_blocks_all_non_read():
    class MockKillSwitch:
        class _Inner:
            enabled = True
        kill_switch = _Inner()

    engine = build_engine()
    engine.oversight = MockKillSwitch()

    read_check = engine.allow_request(
        component="dashboard",
        operation="read_metrics",
        action_category="READ",
    )

    mutate_check = engine.allow_request(
        component="civilization",
        operation="create_task",
        action_category="MUTATE",
    )

    assert read_check.allowed is True
    assert read_check.degradation_mode == DegradationMode.SAFE_STOP
    assert mutate_check.allowed is False
    assert mutate_check.degradation_mode == DegradationMode.SAFE_STOP


def test_resilience_report():
    engine = build_engine(failure_threshold=1, cooldown_seconds=60)
    engine.policy.open_circuit_degradation_threshold = 1

    engine.record_failure(
        component="service",
        operation="op",
        error="fail",
    )

    report = engine.report()

    assert report.circuit_count == 1
    assert report.open_circuit_count == 1
    assert report.recent_failure_count >= 1
    assert report.degradation_mode == DegradationMode.DEGRADED


def test_chaos_drill_quorum_degraded():
    engine = build_engine(failure_threshold=1, cooldown_seconds=60)
    engine.policy.open_circuit_degradation_threshold = 1

    drill = engine.run_chaos_drill(
        name="quorum_loss_drill",
        scenario="quorum_evaluate",
        target_component="federation",
        expected_safe_state="DEGRADED",
        failure_count=1,
    )

    assert drill.passed is True


def test_auto_recovery_from_degraded():
    engine = build_engine(
        failure_threshold=1,
        cooldown_seconds=60,
    )
    engine.policy.open_circuit_degradation_threshold = 1

    engine.record_failure("service", "op", error="fail")
    assert engine.mode == DegradationMode.DEGRADED

    engine.get_circuit("service", "op")
    circuit = engine.circuits["service:op"]
    circuit.state = CircuitState.CLOSED
    circuit.failure_count = 0
    engine._update_degradation_mode()

    assert engine.mode == DegradationMode.NORMAL
