"""Autonomy accounting — the substrate of the Autonomy Certification.

Every cascade outcome is observed; the report exposes exactly the ratios
the certification requires. Thresholds are provisional until the first
measured audit sets them (ledger discipline).
"""

from __future__ import annotations

from tiannara.domain.models.intelligence import (
    IntelligenceResult,
    LocalityLevel,
)

FULL_THRESHOLD = 0.99
PARTIAL_THRESHOLD = 0.95


class AutonomyAccountant:
    def __init__(self) -> None:
        self._tasks_attempted = 0
        self._level_counts = {level: 0 for level in LocalityLevel}
        self._completed_without_external = 0

    def observe(self, result: IntelligenceResult) -> None:
        self._tasks_attempted += 1
        self._level_counts[result.locality] += 1
        if result.locality is not LocalityLevel.L3_EXTERNAL_MODEL:
            self._completed_without_external += 1

    def observe_failure(self) -> None:
        self._tasks_attempted += 1

    def report(self) -> dict:
        attempted = self._tasks_attempted
        external = self._level_counts[LocalityLevel.L3_EXTERNAL_MODEL]
        return {
            "tasks_attempted": attempted,
            "level_counts": {
                f"L{level.value}": count for level, count in self._level_counts.items()
            },
            "external_dependency_ratio": (external / attempted) if attempted else 0.0,
            "keyless_completion_ratio": (
                self._completed_without_external / attempted
            )
            if attempted
            else 1.0,
        }

    def status(self) -> str:
        keyless = self.report()["keyless_completion_ratio"]
        if keyless >= FULL_THRESHOLD:
            return "FULL"
        if keyless >= PARTIAL_THRESHOLD:
            return "PARTIAL"
        return "DEVELOPING"
