"""
Models for operational resilience and safe failure hardening.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class DegradationMode(str, Enum):
    NORMAL = "NORMAL"
    DEGRADED = "DEGRADED"
    READ_ONLY = "READ_ONLY"
    SAFE_STOP = "SAFE_STOP"


class FailureSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class CircuitBreakerConfig(BaseModel):
    """Configuration for a circuit breaker."""

    failure_threshold: int = Field(default=5, ge=1)

    success_threshold_half_open: int = Field(default=2, ge=1)

    cooldown_seconds: int = Field(default=60, ge=0)

    window_seconds: int = Field(default=300, ge=1)


class RetryPolicy(BaseModel):
    """Policy controlling retry behavior."""

    max_attempts: int = Field(default=3, ge=1)

    initial_delay_seconds: float = Field(default=0.1, ge=0.0)

    max_delay_seconds: float = Field(default=5.0, ge=0.0)

    backoff_multiplier: float = Field(default=2.0, ge=1.0)

    budget_window_seconds: int = Field(default=60, ge=1)

    budget_max_attempts: int = Field(default=10, ge=1)


class ResiliencePolicy(BaseModel):
    """Global resilience policy."""

    default_circuit: CircuitBreakerConfig = Field(
        default_factory=CircuitBreakerConfig
    )

    default_retry: RetryPolicy = Field(default_factory=RetryPolicy)

    read_categories: List[str] = Field(
        default_factory=lambda: ["READ"]
    )

    high_impact_fail_closed: bool = True

    open_circuit_degradation_threshold: int = Field(default=3, ge=1)

    auto_recover_from_degraded: bool = True


class FailureEvent(BaseModel):
    """Failure event recorded by the resilience engine."""

    id: str

    component: str
    operation: str

    error: str = ""

    severity: FailureSeverity = FailureSeverity.MEDIUM

    context: Dict[str, Any] = Field(default_factory=dict)

    created_at: str


class CircuitBreakerStatus(BaseModel):
    """State of one circuit breaker."""

    component: str
    operation: str

    state: CircuitState = CircuitState.CLOSED

    failure_count: int = 0
    success_count: int = 0

    last_failure_at: Optional[str] = None
    last_state_change_at: str

    next_attempt_at: Optional[str] = None


class ResilienceCheckResult(BaseModel):
    """Result of a resilience check."""

    allowed: bool

    reason: str

    state: CircuitState

    degradation_mode: DegradationMode

    required_human_approval: bool = False


class RetryDecision(BaseModel):
    """Decision about whether a retry is allowed."""

    allowed: bool

    attempt: int

    delay_seconds: float = 0.0

    reason: str = ""


class QuorumState(BaseModel):
    """Quorum state for a governed group."""

    group_id: str

    total_weight: float
    participating_weight: float

    required_ratio: float

    quorum_met: bool

    evaluated_at: str


class ChaosDrill(BaseModel):
    """Record of a chaos drill."""

    id: str

    name: str
    scenario: str
    target_component: str

    status: str

    expected_safe_state: str
    observed_state: str

    passed: bool

    started_at: str
    completed_at: str


class ResilienceReport(BaseModel):
    """Operational resilience report."""

    generated_at: str

    degradation_mode: DegradationMode

    circuit_count: int = 0
    open_circuit_count: int = 0
    half_open_circuit_count: int = 0

    recent_failure_count: int = 0

    quorum_states: List[QuorumState] = Field(default_factory=list)

    chaos_drill_count: int = 0
