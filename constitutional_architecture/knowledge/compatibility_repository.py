"""
Compatibility Repository — Stores and queries pattern compatibility.
"""

from __future__ import annotations

from typing import Any, Optional

from constitutional_architecture.knowledge.knowledge_types import CompatibilityRecord


class CompatibilityRepository:

    def __init__(self) -> None:
        self._records: dict[tuple[str, str], list[CompatibilityRecord]] = {}

    def record(self, record: CompatibilityRecord) -> None:
        key = tuple(sorted([record.pattern_a, record.pattern_b]))
        self._records.setdefault(key, []).append(record)

    def get_compatibility(self, pattern_a: str, pattern_b: str) -> Optional[float]:
        key = tuple(sorted([pattern_a, pattern_b]))
        records = self._records.get(key)
        if not records:
            return None
        scores = [r.compatibility_score for r in records]
        return sum(scores) / len(scores)

    def get_all_compatible(
        self, pattern_name: str, min_score: float = 0.6
    ) -> list[tuple[str, float]]:
        results: list[tuple[str, float]] = []
        for (a, b), records in self._records.items():
            if a == pattern_name:
                other = b
            elif b == pattern_name:
                other = a
            else:
                continue
            avg_score = sum(r.compatibility_score for r in records) / len(records)
            if avg_score >= min_score:
                results.append((other, avg_score))
        results.sort(key=lambda x: x[1], reverse=True)
        return results

    def get_all_conflicting(
        self, pattern_name: str, max_score: float = 0.4
    ) -> list[tuple[str, float]]:
        results: list[tuple[str, float]] = []
        for (a, b), records in self._records.items():
            if a == pattern_name:
                other = b
            elif b == pattern_name:
                other = a
            else:
                continue
            avg_score = sum(r.compatibility_score for r in records) / len(records)
            if avg_score <= max_score:
                results.append((other, avg_score))
        results.sort(key=lambda x: x[1])
        return results

    def get_pattern_mates(self, pattern_name: str) -> list[str]:
        mates: list[str] = []
        for (a, b) in self._records:
            if a == pattern_name:
                mates.append(b)
            elif b == pattern_name:
                mates.append(a)
        return list(set(mates))

    @property
    def total_pairs(self) -> int:
        return len(self._records)

    @property
    def all_pairs(self) -> list[tuple[str, str]]:
        return list(self._records.keys())
