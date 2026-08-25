from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping

@dataclass(frozen=True)
class SurfaceClassRequirement:
    class_id: str
    allowed_outcomes: tuple[str, ...]
    required_outcomes: tuple[str, ...]

@dataclass(frozen=True)
class SurfaceExerciseContract:
    required_classes: tuple[str, ...]
    class_requirements: Mapping[str, SurfaceClassRequirement]

CONTRACT_004_SURFACE = SurfaceExerciseContract(
    required_classes=("strong_architecture", "weak_architecture", "adversarial_architecture", "human_baseline"),
    class_requirements={
        "strong_architecture": SurfaceClassRequirement("strong_architecture", ("CERTIFIED",), ("CERTIFIED",)),
        "weak_architecture": SurfaceClassRequirement("weak_architecture", ("NOT_CERTIFIED",), ("NOT_CERTIFIED",)),
        "adversarial_architecture": SurfaceClassRequirement("adversarial_architecture", ("CERTIFIED", "NOT_CERTIFIED"), ("CERTIFIED", "NOT_CERTIFIED")),
        "human_baseline": SurfaceClassRequirement("human_baseline", ("CERTIFIED",), ("CERTIFIED",)),
    },
)
