"""Adversarial composition package (R2.8.11)."""
from .composition import (
    AttackPrimitive,
    DefenseLayer,
    CompositeAttack,
    ComposedMutationSpec,
    CompositionVerdict,
    DefenseMatrix,
    analyze_composition,
    vulnerable_matrix,
    hardened_matrix,
    rooted_matrix,
    COMPOSITION_MATRIX,
    ComposedDetectionMetrics,
    ComposedMeasurementSummary,
)

__all__ = [
    "AttackPrimitive",
    "DefenseLayer",
    "CompositeAttack",
    "ComposedMutationSpec",
    "CompositionVerdict",
    "DefenseMatrix",
    "analyze_composition",
    "vulnerable_matrix",
    "hardened_matrix",
    "rooted_matrix",
    "COMPOSITION_MATRIX",
    "ComposedDetectionMetrics",
    "ComposedMeasurementSummary",
]
