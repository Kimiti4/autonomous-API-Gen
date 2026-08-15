"""
Tracing Engine.

Analyzes distributed traces to identify performance bottlenecks
and architectural issues.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from constitutional_architecture.operations.observation_model import (
    Observation,
    ObservationSeverity,
    ObservationSource,
)


@dataclass(frozen=True)
class Span:
    id: str
    trace_id: str
    parent_id: Optional[str] = None
    operation_name: str = ""
    service_name: str = ""
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    duration_ms: float = 0.0
    status: str = "ok"
    tags: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Trace:
    trace_id: str
    spans: tuple[Span, ...] = ()
    start_time: Optional[datetime] = None
    total_duration_ms: float = 0.0
    service_count: int = 0
    span_count: int = 0
    error_count: int = 0

    @property
    def root_span(self) -> Optional[Span]:
        for span in self.spans:
            if span.parent_id is None:
                return span
        return None


class TracingEngine:

    def __init__(
        self,
        slow_threshold_ms: float = 1000.0,
        max_hops: int = 10,
    ) -> None:
        self._traces: list[Trace] = []
        self._slow_threshold = slow_threshold_ms
        self._max_hops = max_hops

    def record_trace(self, trace: Trace) -> None:
        self._traces.append(trace)
        if len(self._traces) > 10000:
            self._traces = self._traces[-10000:]

    def analyze(self, trace: Trace) -> list[Observation]:
        observations: list[Observation] = []

        if trace.total_duration_ms > self._slow_threshold:
            observations.append(Observation(
                id=f"obs-{uuid.uuid4().hex[:12]}",
                source=ObservationSource.TRACES,
                severity=ObservationSeverity.WARNING,
                title=f"Slow trace: {trace.total_duration_ms:.0f}ms",
                description=(
                    f"Trace {trace.trace_id} took {trace.total_duration_ms:.0f}ms "
                    f"across {trace.service_count} services"
                ),
                details={
                    "trace_id": trace.trace_id,
                    "duration_ms": trace.total_duration_ms,
                    "service_count": trace.service_count,
                    "span_count": trace.span_count,
                },
            ))

        if trace.span_count > self._max_hops:
            observations.append(Observation(
                id=f"obs-{uuid.uuid4().hex[:12]}",
                source=ObservationSource.TRACES,
                severity=ObservationSeverity.WARNING,
                title=f"Excessive service hops: {trace.span_count}",
                description=(
                    f"Trace {trace.trace_id} has {trace.span_count} spans "
                    f"(threshold: {self._max_hops})."
                ),
                details={
                    "trace_id": trace.trace_id,
                    "span_count": trace.span_count,
                    "service_count": trace.service_count,
                    "threshold": self._max_hops,
                },
            ))

        if trace.error_count > 0:
            observations.append(Observation(
                id=f"obs-{uuid.uuid4().hex[:12]}",
                source=ObservationSource.TRACES,
                severity=ObservationSeverity.ERROR,
                title=f"Trace has {trace.error_count} error(s)",
                description=f"Trace {trace.trace_id} contains errors",
                details={
                    "trace_id": trace.trace_id,
                    "error_count": trace.error_count,
                },
            ))

        if trace.spans:
            slowest = max(trace.spans, key=lambda s: s.duration_ms)
            if slowest.duration_ms > self._slow_threshold * 0.5:
                observations.append(Observation(
                    id=f"obs-{uuid.uuid4().hex[:12]}",
                    source=ObservationSource.TRACES,
                    severity=ObservationSeverity.WARNING,
                    title=f"Bottleneck: {slowest.operation_name}",
                    description=(
                        f"Span '{slowest.operation_name}' in service "
                        f"'{slowest.service_name}' took {slowest.duration_ms:.0f}ms"
                    ),
                    details={
                        "span_id": slowest.id,
                        "operation": slowest.operation_name,
                        "service": slowest.service_name,
                        "duration_ms": slowest.duration_ms,
                    },
                    service_name=slowest.service_name,
                ))

        return observations

    @property
    def trace_count(self) -> int:
        return len(self._traces)

    @property
    def average_duration_ms(self) -> float:
        if not self._traces:
            return 0.0
        return sum(t.total_duration_ms for t in self._traces) / len(self._traces)
