"""
Operational resilience engine.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from ..utils import deterministic_id, utcnow
from .models import (
    ChaosDrill,
    CircuitBreakerConfig,
    CircuitBreakerStatus,
    CircuitState,
    DegradationMode,
    FailureEvent,
    FailureSeverity,
    QuorumState,
    ResilienceCheckResult,
    ResiliencePolicy,
    ResilienceReport,
    RetryDecision,
)


class ResilienceError(Exception):
    """Base error for resilience operations."""


class ResilienceEngine:
    """Coordinates circuit breakers, degradation, quorum, and chaos drills."""

    def __init__(
        self,
        policy: Optional[ResiliencePolicy] = None,
        oversight_engine=None,
    ) -> None:
        self.policy = policy or ResiliencePolicy()
        self.oversight = oversight_engine

        self.circuits: Dict[str, CircuitBreakerStatus] = {}
        self.failure_events: List[FailureEvent] = []

        self.mode: DegradationMode = DegradationMode.NORMAL

        self.quorum_states: Dict[str, QuorumState] = {}

        self.retry_budgets: Dict[str, Dict] = {}

        self.chaos_drills: List[ChaosDrill] = []

    # ------------------------------------------------------------------
    # Circuit breakers
    # ------------------------------------------------------------------

    def get_circuit(
        self,
        component: str,
        operation: str,
    ) -> CircuitBreakerStatus:
        key = self._circuit_key(component, operation)

        circuit = self.circuits.get(key)

        if circuit:
            return circuit

        now = utcnow().isoformat()

        circuit = CircuitBreakerStatus(
            component=component,
            operation=operation,
            state=CircuitState.CLOSED,
            failure_count=0,
            success_count=0,
            last_state_change_at=now,
        )

        self.circuits[key] = circuit

        return circuit

    def record_success(
        self,
        component: str,
        operation: str,
    ) -> CircuitBreakerStatus:
        circuit = self.get_circuit(component, operation)

        now = utcnow()

        if circuit.state == CircuitState.OPEN:
            if self._can_attempt_from_open(circuit, now):
                circuit.state = CircuitState.HALF_OPEN
                circuit.success_count = 0
                circuit.last_state_change_at = now.isoformat()

        if circuit.state == CircuitState.HALF_OPEN:
            circuit.success_count += 1

            if (
                circuit.success_count
                >= self.policy.default_circuit.success_threshold_half_open
            ):
                circuit.state = CircuitState.CLOSED
                circuit.failure_count = 0
                circuit.success_count = 0
                circuit.next_attempt_at = None
                circuit.last_state_change_at = now.isoformat()

        elif circuit.state == CircuitState.CLOSED:
            circuit.failure_count = 0
            circuit.success_count = 0

        self._update_degradation_mode()

        return circuit

    def record_failure(
        self,
        component: str,
        operation: str,
        error: str = "",
        severity: FailureSeverity = FailureSeverity.MEDIUM,
        context: Optional[Dict] = None,
    ) -> CircuitBreakerStatus:
        circuit = self.get_circuit(component, operation)

        now = utcnow()

        failure_id = deterministic_id(
            "failure_event",
            {
                "component": component,
                "operation": operation,
                "created_at": now.isoformat(),
                "failure_count": len(self.failure_events),
            },
        )

        event = FailureEvent(
            id=failure_id,
            component=component,
            operation=operation,
            error=error,
            severity=severity,
            context=context or {},
            created_at=now.isoformat(),
        )

        self.failure_events.append(event)

        circuit.last_failure_at = now.isoformat()

        if circuit.state == CircuitState.HALF_OPEN:
            circuit.state = CircuitState.OPEN
            circuit.failure_count = (
                self.policy.default_circuit.failure_threshold
            )
            circuit.success_count = 0
            circuit.next_attempt_at = self._next_attempt_time(now)
            circuit.last_state_change_at = now.isoformat()

        elif circuit.state == CircuitState.CLOSED:
            circuit.failure_count += 1

            if (
                circuit.failure_count
                >= self.policy.default_circuit.failure_threshold
            ):
                circuit.state = CircuitState.OPEN
                circuit.success_count = 0
                circuit.next_attempt_at = self._next_attempt_time(now)
                circuit.last_state_change_at = now.isoformat()

        self._update_degradation_mode()

        return circuit

    def allow_request(
        self,
        component: str,
        operation: str,
        action_category: str = "READ",
        high_impact: bool = False,
    ) -> ResilienceCheckResult:
        circuit = self.get_circuit(component, operation)

        now = utcnow()

        kill_switch_active = False

        if self.oversight and hasattr(self.oversight, "kill_switch"):
            kill_switch_active = bool(self.oversight.kill_switch.enabled)

        if kill_switch_active:
            if action_category in self.policy.read_categories and not high_impact:
                return ResilienceCheckResult(
                    allowed=True,
                    reason="Read actions remain allowed during kill switch.",
                    state=circuit.state,
                    degradation_mode=DegradationMode.SAFE_STOP,
                )

            return ResilienceCheckResult(
                allowed=False,
                reason="Kill switch active. Non-read actions blocked.",
                state=circuit.state,
                degradation_mode=DegradationMode.SAFE_STOP,
                required_human_approval=True,
            )

        if self.mode == DegradationMode.SAFE_STOP:
            if action_category in self.policy.read_categories and not high_impact:
                return ResilienceCheckResult(
                    allowed=True,
                    reason="Read actions allowed in SAFE_STOP mode.",
                    state=circuit.state,
                    degradation_mode=self.mode,
                )

            return ResilienceCheckResult(
                allowed=False,
                reason="System is in SAFE_STOP mode.",
                state=circuit.state,
                degradation_mode=self.mode,
                required_human_approval=True,
            )

        if self.mode == DegradationMode.READ_ONLY:
            if action_category in self.policy.read_categories and not high_impact:
                return ResilienceCheckResult(
                    allowed=True,
                    reason="Read actions allowed in READ_ONLY mode.",
                    state=circuit.state,
                    degradation_mode=self.mode,
                )

            return ResilienceCheckResult(
                allowed=False,
                reason="System is in READ_ONLY mode.",
                state=circuit.state,
                degradation_mode=self.mode,
                required_human_approval=True,
            )

        if (
            high_impact
            and self.mode != DegradationMode.NORMAL
            and self.policy.high_impact_fail_closed
        ):
            return ResilienceCheckResult(
                allowed=False,
                reason="High-impact actions fail closed while degraded.",
                state=circuit.state,
                degradation_mode=self.mode,
                required_human_approval=True,
            )

        if circuit.state == CircuitState.OPEN:
            if self._can_attempt_from_open(circuit, now):
                circuit.state = CircuitState.HALF_OPEN
                circuit.success_count = 0
                circuit.last_state_change_at = now.isoformat()

                return ResilienceCheckResult(
                    allowed=True,
                    reason="Circuit moving HALF_OPEN. Probe request allowed.",
                    state=circuit.state,
                    degradation_mode=self.mode,
                )

            return ResilienceCheckResult(
                allowed=False,
                reason="Circuit breaker is OPEN.",
                state=circuit.state,
                degradation_mode=self.mode,
            )

        return ResilienceCheckResult(
            allowed=True,
            reason="Request allowed by resilience policy.",
            state=circuit.state,
            degradation_mode=self.mode,
        )

    # ------------------------------------------------------------------
    # Degradation mode
    # ------------------------------------------------------------------

    def set_degradation_mode(
        self,
        mode: DegradationMode,
        reason: str,
        actor_id: str = "system",
    ) -> DegradationMode:
        self.mode = mode

        self.failure_events.append(
            FailureEvent(
                id=deterministic_id(
                    "degradation_mode_change",
                    {
                        "mode": mode.value,
                        "reason": reason,
                        "actor_id": actor_id,
                        "created_at": utcnow().isoformat(),
                    },
                ),
                component="resilience_engine",
                operation="set_degradation_mode",
                error=reason,
                severity=FailureSeverity.HIGH,
                context={
                    "mode": mode.value,
                    "actor_id": actor_id,
                },
                created_at=utcnow().isoformat(),
            )
        )

        return self.mode

    # ------------------------------------------------------------------
    # Quorum
    # ------------------------------------------------------------------

    def evaluate_quorum(
        self,
        group_id: str,
        total_weight: float,
        participating_weight: float,
        required_ratio: float = 0.5,
    ) -> QuorumState:
        quorum_met = False

        if total_weight > 0:
            quorum_met = (
                participating_weight / total_weight
            ) >= required_ratio

        state = QuorumState(
            group_id=group_id,
            total_weight=total_weight,
            participating_weight=participating_weight,
            required_ratio=required_ratio,
            quorum_met=quorum_met,
            evaluated_at=utcnow().isoformat(),
        )

        self.quorum_states[group_id] = state

        if not quorum_met:
            if self.mode == DegradationMode.NORMAL:
                self.set_degradation_mode(
                    mode=DegradationMode.DEGRADED,
                    reason=f"Quorum lost for group: {group_id}",
                )

        return state

    # ------------------------------------------------------------------
    # Retry budgets
    # ------------------------------------------------------------------

    def retry_decision(
        self,
        operation: str,
        attempt: int,
        error_class: str = "TRANSIENT",
    ) -> RetryDecision:
        retry_policy = self.policy.default_retry

        if attempt >= retry_policy.max_attempts:
            return RetryDecision(
                allowed=False,
                attempt=attempt,
                reason="Maximum retry attempts reached.",
            )

        now = utcnow()

        budget = self.retry_budgets.get(operation)

        if not budget:
            budget = {
                "count": 0,
                "window_start": now,
            }

            self.retry_budgets[operation] = budget

        window_start = budget["window_start"]

        elapsed = (now - window_start).total_seconds()

        if elapsed >= retry_policy.budget_window_seconds:
            budget["count"] = 0
            budget["window_start"] = now

        if budget["count"] >= retry_policy.budget_max_attempts:
            return RetryDecision(
                allowed=False,
                attempt=attempt,
                reason="Retry budget exhausted.",
            )

        delay = min(
            retry_policy.max_delay_seconds,
            retry_policy.initial_delay_seconds
            * (retry_policy.backoff_multiplier ** attempt),
        )

        budget["count"] += 1

        return RetryDecision(
            allowed=True,
            attempt=attempt,
            delay_seconds=delay,
            reason="Retry allowed.",
        )

    # ------------------------------------------------------------------
    # Chaos drills
    # ------------------------------------------------------------------

    def run_chaos_drill(
        self,
        name: str,
        scenario: str,
        target_component: str,
        expected_safe_state: str = "OPEN",
        failure_count: Optional[int] = None,
    ) -> ChaosDrill:
        started_at = utcnow()

        failures = (
            failure_count
            or self.policy.default_circuit.failure_threshold
        )

        for index in range(failures):
            self.record_failure(
                component=target_component,
                operation=scenario,
                error=f"Chaos drill failure {index + 1}",
                severity=FailureSeverity.HIGH,
                context={
                    "chaos_drill": name,
                },
            )

        circuit = self.get_circuit(target_component, scenario)

        observed_state = circuit.state.value

        if expected_safe_state == "DEGRADED":
            passed = self.mode in {
                DegradationMode.DEGRADED,
                DegradationMode.READ_ONLY,
                DegradationMode.SAFE_STOP,
            }
        else:
            passed = observed_state == expected_safe_state

        completed_at = utcnow()

        drill_id = deterministic_id(
            "chaos_drill",
            {
                "name": name,
                "scenario": scenario,
                "target_component": target_component,
                "started_at": started_at.isoformat(),
            },
        )

        drill = ChaosDrill(
            id=drill_id,
            name=name,
            scenario=scenario,
            target_component=target_component,
            status="PASS" if passed else "FAIL",
            expected_safe_state=expected_safe_state,
            observed_state=observed_state,
            passed=passed,
            started_at=started_at.isoformat(),
            completed_at=completed_at.isoformat(),
        )

        self.chaos_drills.append(drill)

        return drill

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def report(self) -> ResilienceReport:
        open_circuits = sum(
            1
            for circuit in self.circuits.values()
            if circuit.state == CircuitState.OPEN
        )

        half_open_circuits = sum(
            1
            for circuit in self.circuits.values()
            if circuit.state == CircuitState.HALF_OPEN
        )

        recent_failures = self.failure_events[-100:]

        return ResilienceReport(
            generated_at=utcnow().isoformat(),
            degradation_mode=self.mode,
            circuit_count=len(self.circuits),
            open_circuit_count=open_circuits,
            half_open_circuit_count=half_open_circuits,
            recent_failure_count=len(recent_failures),
            quorum_states=list(self.quorum_states.values()),
            chaos_drill_count=len(self.chaos_drills),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _circuit_key(self, component: str, operation: str) -> str:
        return f"{component}:{operation}"

    def _next_attempt_time(self, now):
        from datetime import timedelta

        cooldown = self.policy.default_circuit.cooldown_seconds

        return (now + timedelta(seconds=cooldown)).isoformat()

    def _can_attempt_from_open(
        self,
        circuit: CircuitBreakerStatus,
        now,
    ) -> bool:
        if not circuit.next_attempt_at:
            return True

        next_attempt = self._parse_timestamp(circuit.next_attempt_at)

        return now >= next_attempt

    def _update_degradation_mode(self) -> None:
        open_circuits = sum(
            1
            for circuit in self.circuits.values()
            if circuit.state == CircuitState.OPEN
        )

        if (
            open_circuits
            >= self.policy.open_circuit_degradation_threshold
        ):
            if self.mode == DegradationMode.NORMAL:
                self.set_degradation_mode(
                    mode=DegradationMode.DEGRADED,
                    reason="Too many open circuit breakers.",
                )

            return

        if (
            self.policy.auto_recover_from_degraded
            and open_circuits == 0
            and self.mode == DegradationMode.DEGRADED
        ):
            self.set_degradation_mode(
                mode=DegradationMode.NORMAL,
                reason="All circuit breakers recovered.",
            )

    def _parse_timestamp(self, value: str):
        from datetime import datetime, timezone

        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return utcnow()

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)

        return parsed
