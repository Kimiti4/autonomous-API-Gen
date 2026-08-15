"""
Cost Analyzer.

Attributes infrastructure costs to architectural decisions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from constitutional_architecture.operations.observation_model import (
    Observation,
    ObservationSeverity,
    ObservationSource,
)


@dataclass(frozen=True)
class CostEntry:
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    service_name: str = ""
    resource_type: str = ""
    amount: float = 0.0
    currency: str = "USD"
    deployment_id: str = ""
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class CostReport:
    total_cost: float = 0.0
    by_service: dict[str, float] = field(default_factory=dict)
    by_resource_type: dict[str, float] = field(default_factory=dict)
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    cost_per_request: float = 0.0
    recommendations: tuple[str, ...] = ()


class CostAnalyzer:

    def __init__(self) -> None:
        self._entries: list[CostEntry] = []

    def record(self, entry: CostEntry) -> None:
        self._entries.append(entry)

    def analyze(self) -> CostReport:
        if not self._entries:
            return CostReport()

        by_service: dict[str, float] = {}
        by_resource: dict[str, float] = {}
        total = 0.0

        for entry in self._entries:
            total += entry.amount
            by_service[entry.service_name] = by_service.get(entry.service_name, 0.0) + entry.amount
            by_resource[entry.resource_type] = by_resource.get(entry.resource_type, 0.0) + entry.amount

        recommendations: list[str] = []
        if by_service:
            avg_cost = total / len(by_service)
            expensive = [s for s, c in by_service.items() if c > avg_cost * 2]
            if expensive:
                recommendations.append(
                    f"Services {expensive} cost >2x average; consider optimization"
                )

        compute_ratio = by_resource.get("compute", 0.0) / total if total > 0 else 0.0
        if compute_ratio > 0.7:
            recommendations.append(
                f"Compute costs dominate ({compute_ratio:.0%}); consider auto-scaling or reserved instances"
            )

        return CostReport(
            total_cost=total, by_service=by_service,
            by_resource_type=by_resource,
            period_start=self._entries[0].timestamp if self._entries else None,
            period_end=self._entries[-1].timestamp if self._entries else None,
            recommendations=tuple(recommendations),
        )

    def produce_observations(self) -> list[Observation]:
        report = self.analyze()
        observations: list[Observation] = []
        for recommendation in report.recommendations:
            observations.append(Observation(
                id=f"obs-cost-{len(observations)}",
                source=ObservationSource.COST_REPORTING,
                severity=ObservationSeverity.WARNING,
                title="Cost optimization opportunity",
                description=recommendation,
                details={"total_cost": report.total_cost},
            ))
        return observations

    @property
    def total_entries(self) -> int:
        return len(self._entries)
