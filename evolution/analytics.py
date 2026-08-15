"""
Campaign analytics for multi-generation evolution.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .models import utcnow


class ObjectiveTrendPoint(BaseModel):
    """One point in an objective trend."""

    generation_index: int
    value: Optional[float] = None


class CampaignObjectiveTrend(BaseModel):
    """Trend for one objective across generations."""

    campaign_id: str
    objective: str

    points: List[ObjectiveTrendPoint] = Field(default_factory=list)


class CampaignAnalyticsReport(BaseModel):
    """Analytics report for an evolution campaign."""

    campaign_id: str

    generation_count: int = 0
    feasible_generation_count: int = 0

    selected_candidate_ids: List[str] = Field(default_factory=list)

    elite_count: int = 0

    objective_trends: Dict[str, List[Optional[float]]] = Field(
        default_factory=dict
    )

    average_objectives: Dict[str, Optional[float]] = Field(
        default_factory=dict
    )

    objective_deltas: Dict[str, Optional[float]] = Field(
        default_factory=dict
    )

    objectives_improved: int = 0
    objectives_regressed: int = 0

    stagnation_detected: bool = False

    generation_statuses: Dict[str, int] = Field(default_factory=dict)

    promotion_event_counts: Dict[str, int] = Field(default_factory=dict)

    created_at: str


class CampaignAnalyticsEngine:
    """Computes analytics from evolutionary memory and observability."""

    def __init__(
        self,
        memory=None,
        observability_bus=None,
    ) -> None:
        self.memory = memory
        self.observability_bus = observability_bus

    def campaign_report(self, campaign_id: str) -> CampaignAnalyticsReport:
        summaries = []

        if self.memory:
            summaries = self.memory.list_generation_summaries(campaign_id)

        elites = []

        if self.memory:
            elites = self.memory.list_elites(campaign_id)

        objective_trends = self._build_objective_trends(summaries)

        average_objectives = self._average_objectives(objective_trends)

        objective_deltas = self._objective_deltas(objective_trends)

        objectives_improved = 0
        objectives_regressed = 0

        for delta in objective_deltas.values():
            if delta is None:
                continue

            if delta > 1e-6:
                objectives_improved += 1
            elif delta < -1e-6:
                objectives_regressed += 1

        stagnation_detected = False

        if summaries and objective_deltas:
            stagnation_detected = all(
                abs(delta) <= 1e-6
                for delta in objective_deltas.values()
                if delta is not None
            )

        feasible_generation_count = sum(
            1
            for summary in summaries
            if getattr(summary, "selected_candidate_id", None)
        )

        generation_statuses: Dict[str, int] = {}

        for summary in summaries:
            status = str(getattr(summary, "status", "UNKNOWN"))

            generation_statuses[status] = (
                generation_statuses.get(status, 0) + 1
            )

        promotion_event_counts = self._promotion_event_counts(campaign_id)

        return CampaignAnalyticsReport(
            campaign_id=campaign_id,
            generation_count=len(summaries),
            feasible_generation_count=feasible_generation_count,
            selected_candidate_ids=[
                getattr(summary, "selected_candidate_id", None)
                for summary in summaries
                if getattr(summary, "selected_candidate_id", None)
            ],
            elite_count=len(elites),
            objective_trends=objective_trends,
            average_objectives=average_objectives,
            objective_deltas=objective_deltas,
            objectives_improved=objectives_improved,
            objectives_regressed=objectives_regressed,
            stagnation_detected=stagnation_detected,
            generation_statuses=generation_statuses,
            promotion_event_counts=promotion_event_counts,
            created_at=utcnow().isoformat(),
        )

    def objective_trend(
        self,
        campaign_id: str,
        objective: str,
    ) -> CampaignObjectiveTrend:
        report = self.campaign_report(campaign_id)

        values = report.objective_trends.get(objective, [])

        points = [
            ObjectiveTrendPoint(
                generation_index=index + 1,
                value=value,
            )
            for index, value in enumerate(values)
        ]

        return CampaignObjectiveTrend(
            campaign_id=campaign_id,
            objective=objective,
            points=points,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_objective_trends(
        self,
        summaries: List[Any],
    ) -> Dict[str, List[Optional[float]]]:
        objective_names: set[str] = set()

        for summary in summaries:
            objectives = getattr(summary, "objectives", {})

            for objective_name in objectives.keys():
                objective_names.add(objective_name)

        trends: Dict[str, List[Optional[float]]] = {
            objective_name: []
            for objective_name in sorted(objective_names)
        }

        for summary in summaries:
            objectives = getattr(summary, "objectives", {})

            for objective_name in trends.keys():
                value = objectives.get(objective_name)

                if value is None:
                    trends[objective_name].append(None)
                else:
                    trends[objective_name].append(float(value))

        return trends

    def _average_objectives(
        self,
        objective_trends: Dict[str, List[Optional[float]]],
    ) -> Dict[str, Optional[float]]:
        averages: Dict[str, Optional[float]] = {}

        for objective_name, values in objective_trends.items():
            numeric_values = [
                value
                for value in values
                if value is not None
            ]

            if not numeric_values:
                averages[objective_name] = None
            else:
                averages[objective_name] = round(
                    sum(numeric_values) / len(numeric_values),
                    6,
                )

        return averages

    def _objective_deltas(
        self,
        objective_trends: Dict[str, List[Optional[float]]],
    ) -> Dict[str, Optional[float]]:
        deltas: Dict[str, Optional[float]] = {}

        for objective_name, values in objective_trends.items():
            numeric_values = [
                value
                for value in values
                if value is not None
            ]

            if len(numeric_values) < 2:
                deltas[objective_name] = None
            else:
                deltas[objective_name] = round(
                    numeric_values[-1] - numeric_values[0],
                    6,
                )

        return deltas

    def _promotion_event_counts(self, campaign_id: str) -> Dict[str, int]:
        if not self.observability_bus:
            return {}

        events = self.observability_bus.list_events(
            campaign_id=campaign_id,
            limit=10_000,
        )

        promotion_prefix = "PROMOTION_"

        counts: Dict[str, int] = {}

        for event in events:
            event_type = event.event_type.value

            if event_type.startswith(promotion_prefix):
                counts[event_type] = counts.get(event_type, 0) + 1

        return counts
