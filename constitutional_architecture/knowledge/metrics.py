"""
Knowledge Metrics.

Tracks usage, effectiveness, and health of the knowledge engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class KnowledgeMetricsSnapshot:
    total_patterns: int = 0
    total_anti_patterns: int = 0
    total_mutation_records: int = 0
    total_fitness_records: int = 0
    total_compatibility_records: int = 0
    total_lessons: int = 0
    total_queries: int = 0
    total_recommendations: int = 0
    recommendations_accepted: int = 0
    avg_confidence: float = 0.0
    last_updated: Optional[datetime] = None
    hit_rate: float = 0.0
    query_latency_ms: float = 0.0


class KnowledgeMetrics:

    def __init__(self) -> None:
        self._queries: int = 0
        self._hits: int = 0
        self._recommendations: int = 0
        self._recommendations_accepted: int = 0
        self._query_latencies: list[float] = []

    def record_query(self, hit: bool, latency_ms: float) -> None:
        self._queries += 1
        if hit:
            self._hits += 1
        self._query_latencies.append(latency_ms)
        if len(self._query_latencies) > 10000:
            self._query_latencies = self._query_latencies[-10000:]

    def record_recommendation(self, accepted: bool = False) -> None:
        self._recommendations += 1
        if accepted:
            self._recommendations_accepted += 1

    def snapshot(
        self,
        total_patterns: int = 0,
        total_anti_patterns: int = 0,
        total_mutation_records: int = 0,
        total_fitness_records: int = 0,
        total_compatibility_records: int = 0,
        total_lessons: int = 0,
    ) -> KnowledgeMetricsSnapshot:
        avg_latency = (
            sum(self._query_latencies) / len(self._query_latencies)
            if self._query_latencies else 0.0
        )
        hit_rate = self._hits / self._queries if self._queries > 0 else 0.0
        return KnowledgeMetricsSnapshot(
            total_patterns=total_patterns,
            total_anti_patterns=total_anti_patterns,
            total_mutation_records=total_mutation_records,
            total_fitness_records=total_fitness_records,
            total_compatibility_records=total_compatibility_records,
            total_lessons=total_lessons,
            total_queries=self._queries,
            total_recommendations=self._recommendations,
            recommendations_accepted=self._recommendations_accepted,
            avg_confidence=avg_latency,
            hit_rate=hit_rate,
            query_latency_ms=avg_latency,
        )

    @property
    def query_hit_rate(self) -> float:
        return self._hits / self._queries if self._queries > 0 else 0.0

    @property
    def total_queries(self) -> int:
        return self._queries

    @property
    def total_recommendations(self) -> int:
        return self._recommendations

    @property
    def recommendation_acceptance_rate(self) -> float:
        if self._recommendations == 0:
            return 0.0
        return self._recommendations_accepted / self._recommendations
