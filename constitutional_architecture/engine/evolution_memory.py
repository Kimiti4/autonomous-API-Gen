"""
Evolution Memory.

Persists learning across evolution runs. Stores successful mutations,
failed mutations, architecture patterns, and fitness improvements.
Learning must survive process restarts.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


@dataclass(frozen=True)
class MemoryEntry:
    entry_type: str
    content: dict[str, Any] = field(default_factory=dict)
    fitness_impact: float = 0.0
    generation: int = 0
    run_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    confidence: float = 0.0


class EvolutionMemory:
    """
    Persistent evolution memory.

    Stores:
    - Successful mutations (what worked)
    - Failed mutations (what didn't)
    - Architecture patterns (recurring structures)
    - Fitness improvements (what led to gains)
    - Mutation sequences (effective chains)
    - Population statistics (historical trends)
    - Historical Pareto fronts

    Survives process restarts via file persistence.
    """

    def __init__(self, storage_path: Optional[str | Path] = None) -> None:
        self._storage_path = Path(storage_path) if storage_path else None
        self._entries: list[MemoryEntry] = []
        self._max_entries: int = 10000

        if self._storage_path and self._storage_path.exists():
            self._load()

    def record(self, entry: MemoryEntry) -> None:
        self._entries.append(entry)
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries:]
        if self._storage_path:
            self._save()

    def record_success(
        self,
        mutation_type: str,
        fitness_delta: float,
        context: str = "",
        generation: int = 0,
        run_id: str = "",
    ) -> None:
        self.record(MemoryEntry(
            entry_type="successful_mutation",
            content={"mutation_type": mutation_type, "context": context},
            fitness_impact=fitness_delta,
            generation=generation,
            run_id=run_id,
            confidence=min(1.0, abs(fitness_delta) * 10),
        ))

    def record_failure(
        self,
        mutation_type: str,
        reason: str = "",
        generation: int = 0,
        run_id: str = "",
    ) -> None:
        self.record(MemoryEntry(
            entry_type="failed_mutation",
            content={"mutation_type": mutation_type, "reason": reason},
            generation=generation,
            run_id=run_id,
        ))

    def record_pattern(
        self,
        pattern_name: str,
        description: str = "",
        fitness_impact: float = 0.0,
    ) -> None:
        self.record(MemoryEntry(
            entry_type="pattern",
            content={"name": pattern_name, "description": description},
            fitness_impact=fitness_impact,
        ))

    def query_successful(self, mutation_type: Optional[str] = None, limit: int = 50) -> list[MemoryEntry]:
        entries = [e for e in self._entries if e.entry_type == "successful_mutation"]
        if mutation_type:
            entries = [
                e for e in entries
                if e.content.get("mutation_type") == mutation_type
            ]
        return sorted(entries, key=lambda e: e.fitness_impact, reverse=True)[:limit]

    def query_failures(self, mutation_type: Optional[str] = None, limit: int = 50) -> list[MemoryEntry]:
        entries = [e for e in self._entries if e.entry_type == "failed_mutation"]
        if mutation_type:
            entries = [
                e for e in entries
                if e.content.get("mutation_type") == mutation_type
            ]
        return entries[:limit]

    def get_success_rate(self, mutation_type: str) -> float:
        successes = len([
            e for e in self._entries
            if e.entry_type == "successful_mutation"
            and e.content.get("mutation_type") == mutation_type
        ])
        failures = len([
            e for e in self._entries
            if e.entry_type == "failed_mutation"
            and e.content.get("mutation_type") == mutation_type
        ])
        total = successes + failures
        return successes / total if total > 0 else 0.5

    @property
    def entry_count(self) -> int:
        return len(self._entries)

    def _save(self) -> None:
        if self._storage_path is None:
            return
        data = [
            {
                "entry_type": e.entry_type,
                "content": e.content,
                "fitness_impact": e.fitness_impact,
                "generation": e.generation,
                "run_id": e.run_id,
                "timestamp": e.timestamp,
                "confidence": e.confidence,
            }
            for e in self._entries[-1000:]
        ]
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._storage_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _load(self) -> None:
        if self._storage_path is None or not self._storage_path.exists():
            return
        try:
            data = json.loads(self._storage_path.read_text(encoding="utf-8"))
            self._entries = [
                MemoryEntry(
                    entry_type=d.get("entry_type", ""),
                    content=d.get("content", {}),
                    fitness_impact=d.get("fitness_impact", 0.0),
                    generation=d.get("generation", 0),
                    run_id=d.get("run_id", ""),
                    timestamp=d.get("timestamp", ""),
                    confidence=d.get("confidence", 0.0),
                )
                for d in data
            ]
        except (json.JSONDecodeError, KeyError):
            self._entries = []
