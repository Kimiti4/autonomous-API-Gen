"""
Fitness Repository — Stores and queries fitness impact data.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Optional

from constitutional_architecture.knowledge.knowledge_types import FitnessRecord


@dataclass
class FitnessPrediction:
    mutation_type: str
    expected_delta: dict[str, float] = field(default_factory=dict)
    confidence: float = 0.0
    sample_size: int = 0


class FitnessRepository:

    def __init__(self) -> None:
        self._records: dict[str, list[FitnessRecord]] = defaultdict(list)

    def record(self, record: FitnessRecord) -> None:
        self._records[record.mutation_type].append(record)

    def get_records(
        self, mutation_type: Optional[str] = None, context: Optional[str] = None
    ) -> list[FitnessRecord]:
        if mutation_type:
            results = list(self._records.get(mutation_type, []))
        else:
            results = [r for records in self._records.values() for r in records]

        if context:
            results = [r for r in results if r.context == context]

        return results

    def predict(self, mutation_type: str, context: str = "") -> FitnessPrediction:
        records = self._records.get(mutation_type, [])
        if context:
            records = [r for r in records if r.context == context]

        if not records:
            return FitnessPrediction(
                mutation_type=mutation_type,
                expected_delta={}, confidence=0.0, sample_size=0,
            )

        all_dims: set[str] = set()
        for r in records:
            all_dims.update(r.avg_fitness_delta.keys())

        avg_delta = {}
        for dim in all_dims:
            values = [r.avg_fitness_delta.get(dim, 0.0) for r in records]
            avg_delta[dim] = sum(values) / len(values)

        total_samples = sum(r.sample_size for r in records)
        confidence = min(1.0, total_samples / 50.0)
        sample_size = len(records)

        return FitnessPrediction(
            mutation_type=mutation_type,
            expected_delta=avg_delta,
            confidence=confidence,
            sample_size=sample_size,
        )

    def get_impact_summary(self, mutation_type: str) -> dict[str, Any]:
        records = self._records.get(mutation_type, [])
        if not records:
            return {"mutation_type": mutation_type, "total_records": 0}

        all_dims: set[str] = set()
        for r in records:
            all_dims.update(r.dimensions.keys())

        avg_impact = {}
        for dim in all_dims:
            values = [r.dimensions.get(dim, 0.0) for r in records]
            avg_impact[dim] = sum(values) / len(values)

        return {
            "mutation_type": mutation_type,
            "total_records": len(records),
            "total_samples": sum(r.sample_size for r in records),
            "average_impact": avg_impact,
            "contexts": list(set(r.context for r in records if r.context)),
        }

    @property
    def all_mutation_types(self) -> list[str]:
        return list(self._records.keys())

    @property
    def total_records(self) -> int:
        return sum(len(records) for records in self._records.values())
