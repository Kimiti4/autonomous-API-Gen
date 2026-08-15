"""
Phase 5: Evaluator Plugin Interface.

Evaluators do not read CSS or React code. They analyze the Frontend ISR
and return a normalized FitnessScore. This enables the Plugin-First Architecture.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class FitnessDimension:
    name: str
    score: float
    weight: float = 1.0
    violations: tuple[str, ...] = ()


class IFitnessEvaluator(ABC):
    @property
    @abstractmethod
    def dimension_name(self) -> str:
        ...

    @abstractmethod
    def evaluate(self, isr_profile: Any, compiled_artifacts: Optional[Any] = None) -> FitnessDimension:
        ...
