"""
Knowledge Persistence.

Serialization and deserialization for the knowledge engine.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from constitutional_architecture.knowledge.knowledge_types import (
    CompatibilityRecord,
    ConfidenceLevel,
    DomainFact,
    EvolutionLesson,
    FitnessRecord,
    HeuristicRule,
    KnowledgeCategory,
    KnowledgeProvenance,
)


class KnowledgeSerializer:

    @staticmethod
    def fitness_record_to_dict(record: FitnessRecord) -> dict[str, Any]:
        return {
            "mutation_type": record.mutation_type,
            "dimensions": dict(record.dimensions),
            "sample_size": record.sample_size,
            "context": record.context,
            "avg_fitness_delta": dict(record.avg_fitness_delta),
            "timestamp": record.timestamp.isoformat(),
        }

    @staticmethod
    def fitness_record_from_dict(data: dict[str, Any]) -> FitnessRecord:
        return FitnessRecord(
            mutation_type=data["mutation_type"],
            dimensions=data.get("dimensions", {}),
            sample_size=data.get("sample_size", 1),
            context=data.get("context", ""),
            avg_fitness_delta=data.get("avg_fitness_delta", {}),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.now(),
        )

    @staticmethod
    def compatibility_to_dict(record: CompatibilityRecord) -> dict[str, Any]:
        return {
            "pattern_a": record.pattern_a,
            "pattern_b": record.pattern_b,
            "compatibility_score": record.compatibility_score,
            "sample_size": record.sample_size,
            "evidence": list(record.evidence),
            "timestamp": record.timestamp.isoformat(),
        }

    @staticmethod
    def compatibility_from_dict(data: dict[str, Any]) -> CompatibilityRecord:
        return CompatibilityRecord(
            pattern_a=data["pattern_a"],
            pattern_b=data["pattern_b"],
            compatibility_score=data.get("compatibility_score", 0.5),
            sample_size=data.get("sample_size", 1),
            evidence=tuple(data.get("evidence", [])),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.now(),
        )

    @staticmethod
    def lesson_to_dict(lesson: EvolutionLesson) -> dict[str, Any]:
        return {
            "title": lesson.title,
            "description": lesson.description,
            "context": lesson.context,
            "recommendations": list(lesson.recommendations),
            "severity": lesson.severity,
            "source_run_id": lesson.source_run_id,
            "timestamp": lesson.timestamp.isoformat(),
        }

    @staticmethod
    def lesson_from_dict(data: dict[str, Any]) -> EvolutionLesson:
        return EvolutionLesson(
            title=data["title"],
            description=data["description"],
            context=data.get("context", ""),
            recommendations=tuple(data.get("recommendations", [])),
            severity=data.get("severity", "info"),
            source_run_id=data.get("source_run_id", ""),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.now(),
        )


class KnowledgePersistence:

    def __init__(self, storage_path: str | Path) -> None:
        self._path = Path(storage_path)

    def save_fitness_records(
        self, records: list[FitnessRecord], filename: str = "fitness_records.json"
    ) -> None:
        self._path.mkdir(parents=True, exist_ok=True)
        data = [KnowledgeSerializer.fitness_record_to_dict(r) for r in records]
        (self._path / filename).write_text(
            json.dumps(data, indent=2, default=str), encoding="utf-8"
        )

    def load_fitness_records(
        self, filename: str = "fitness_records.json"
    ) -> list[FitnessRecord]:
        path = self._path / filename
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return [KnowledgeSerializer.fitness_record_from_dict(d) for d in data]
        except (json.JSONDecodeError, KeyError):
            return []

    def save_compatibility_records(
        self, records: list[CompatibilityRecord], filename: str = "compatibility.json"
    ) -> None:
        self._path.mkdir(parents=True, exist_ok=True)
        data = [KnowledgeSerializer.compatibility_to_dict(r) for r in records]
        (self._path / filename).write_text(
            json.dumps(data, indent=2, default=str), encoding="utf-8"
        )

    def load_compatibility_records(
        self, filename: str = "compatibility.json"
    ) -> list[CompatibilityRecord]:
        path = self._path / filename
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return [KnowledgeSerializer.compatibility_from_dict(d) for d in data]
        except (json.JSONDecodeError, KeyError):
            return []

    def save_lessons(
        self, lessons: list[EvolutionLesson], filename: str = "lessons.json"
    ) -> None:
        self._path.mkdir(parents=True, exist_ok=True)
        data = [KnowledgeSerializer.lesson_to_dict(l) for l in lessons]
        (self._path / filename).write_text(
            json.dumps(data, indent=2, default=str), encoding="utf-8"
        )

    def load_lessons(
        self, filename: str = "lessons.json"
    ) -> list[EvolutionLesson]:
        path = self._path / filename
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return [KnowledgeSerializer.lesson_from_dict(d) for d in data]
        except (json.JSONDecodeError, KeyError):
            return []
