"""
Reliability Analyzer.

Analyzes SLOs, SLIs, and failure patterns.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

from constitutional_architecture.operations.incident_engine import IncidentEngine
from constitutional_architecture.operations.observation_model import Incident, ObservationSeverity


@dataclass(frozen=True)
class SLO:
    name: str
    metric: str
    target: float
    window: timedelta = field(default_factory=lambda: timedelta(days=30))
    description: str = ""


@dataclass(frozen=True)
class SLIReport:
    slo_name: str
    current_value: float = 0.0
    target: float = 0.0
    met: bool = False
    error_budget_remaining: float = 0.0
    window_start: Optional[datetime] = None
    window_end: Optional[datetime] = None


class ReliabilityAnalyzer:

    def __init__(self) -> None:
        self._slos: list[SLO] = []
        self._availability_data: dict[str, list[tuple[datetime, bool]]] = {}

    def register_slo(self, slo: SLO) -> None:
        self._slos.append(slo)

    def record_availability(
        self,
        service_name: str,
        timestamp: datetime,
        is_available: bool,
    ) -> None:
        self._availability_data.setdefault(service_name, []).append(
            (timestamp, is_available)
        )

    def compute_availability(
        self,
        service_name: str,
        window: Optional[timedelta] = None,
    ) -> float:
        data = self._availability_data.get(service_name, [])
        if not data:
            return 0.0
        if window is None:
            window = timedelta(days=30)
        cutoff = datetime.now(timezone.utc) - window
        recent = [(t, a) for t, a in data if t >= cutoff]
        if not recent:
            return 0.0
        available = sum(1 for _, a in recent if a)
        return available / len(recent)

    def compute_mttr(self, incidents: list[Incident]) -> float:
        if not incidents:
            return 0.0
        durations = [i.duration_seconds for i in incidents if i.duration_seconds > 0]
        if not durations:
            return 0.0
        return sum(durations) / len(durations)

    def compute_mtbf(self, incidents: list[Incident]) -> float:
        if len(incidents) < 2:
            return 0.0
        sorted_incidents = sorted(incidents, key=lambda i: i.timestamp)
        intervals = []
        for i in range(1, len(sorted_incidents)):
            delta = (sorted_incidents[i].timestamp - sorted_incidents[i - 1].timestamp).total_seconds()
            intervals.append(delta)
        return sum(intervals) / len(intervals) if intervals else 0.0

    def evaluate_slo(self, slo: SLO, service_name: str) -> SLIReport:
        current = self.compute_availability(service_name, slo.window)
        met = current >= slo.target
        error_budget = 1.0 - slo.target
        consumed = max(0.0, (1.0 - current) - (1.0 - slo.target))
        remaining = max(0.0, error_budget - consumed)
        return SLIReport(
            slo_name=slo.name, current_value=current,
            target=slo.target, met=met,
            error_budget_remaining=remaining,
        )

    @property
    def registered_slos(self) -> list[SLO]:
        return list(self._slos)
