"""
Mutation Repository — Stores mutation history and outcomes.
"""

from __future__ import annotations

import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from constitutional_architecture.knowledge.knowledge_types import (
    FitnessRecord,
    KnowledgeCategory,
)
from constitutional_architecture.knowledge.knowledge_graph import (
    KnowledgeGraph,
    KnowledgeNode,
    KnowledgeEdge,
    RELATION_LEADS_TO,
)


@dataclass
class MutationRecordEntry:
    operator_name: str
    target_context: str
    fitness_before: dict[str, float] = field(default_factory=dict)
    fitness_after: dict[str, float] = field(default_factory=dict)
    fitness_delta: dict[str, float] = field(default_factory=dict)
    accepted: bool = False
    generation: int = 0
    isr_hash: str = ""
    notes: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    record_id: str = ""


class MutationRepository:

    def __init__(self, graph: Optional[KnowledgeGraph] = None) -> None:
        self._graph = graph or KnowledgeGraph()
        self._records: dict[str, MutationRecordEntry] = {}
        self._fitness_records: list[FitnessRecord] = []

    def record_mutation(self, entry: MutationRecordEntry) -> str:
        rid = entry.record_id or f"mut-{uuid.uuid4().hex[:12]}"
        self._records[rid] = entry

        self._graph.add_node(KnowledgeNode(
            node_id=rid, category=KnowledgeCategory.MUTATION_RECORD,
            label=f"{entry.operator_name}@{entry.generation}",
            description=f"Mutation '{entry.operator_name}' on {entry.target_context}",
            attributes={
                "operator": entry.operator_name,
                "accepted": entry.accepted,
                "generation": entry.generation,
                "fitness_delta": entry.fitness_delta,
            },
        ))
        return rid

    def record_fitness(self, record: FitnessRecord) -> None:
        self._fitness_records.append(record)

    def get(self, record_id: str) -> Optional[MutationRecordEntry]:
        return self._records.get(record_id)

    def query(
        self,
        operator_name: Optional[str] = None,
        accepted_only: bool = False,
        min_generation: int = 0,
        max_results: int = 100,
    ) -> list[MutationRecordEntry]:
        results = list(self._records.values())
        if operator_name:
            results = [r for r in results if r.operator_name == operator_name]
        if accepted_only:
            results = [r for r in results if r.accepted]
        if min_generation > 0:
            results = [r for r in results if r.generation >= min_generation]
        results.sort(key=lambda r: r.timestamp, reverse=True)
        return results[:max_results]

    def get_operator_success_rate(self, operator_name: str) -> float:
        relevant = [r for r in self._records.values() if r.operator_name == operator_name]
        if not relevant:
            return 0.5
        accepted = sum(1 for r in relevant if r.accepted)
        return accepted / len(relevant)

    def get_average_fitness_delta(
        self, operator_name: str, dimension: str
    ) -> float:
        relevant = [
            r for r in self._records.values()
            if r.operator_name == operator_name and r.accepted
        ]
        if not relevant:
            return 0.0
        deltas = [r.fitness_delta.get(dimension, 0.0) for r in relevant]
        return sum(deltas) / len(deltas)

    def get_most_successful_operators(self, top_n: int = 5) -> list[tuple[str, float]]:
        operator_counts: dict[str, list[bool]] = {}
        for r in self._records.values():
            operator_counts.setdefault(r.operator_name, []).append(r.accepted)
        rates = {
            op: sum(results) / len(results)
            for op, results in operator_counts.items()
            if len(results) >= 3
        }
        sorted_ops = sorted(rates.items(), key=lambda x: x[1], reverse=True)
        return sorted_ops[:top_n]

    @property
    def total_mutations(self) -> int:
        return len(self._records)

    @property
    def total_fitness_records(self) -> int:
        return len(self._fitness_records)

    @property
    def operator_names(self) -> list[str]:
        return list(set(r.operator_name for r in self._records.values()))
