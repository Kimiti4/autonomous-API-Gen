"""
Validation — Architectural Type Checking

The validation engine is not merely a graph correctness checker. It is an
architectural type checker analogous to the semantic analysis phase of a
compiler. It performs structural validation, type validation, reference
resolution, reachability analysis, permission consistency, dependency
satisfaction, and completeness checks.
"""

from constitutional_architecture.validation.checker import (
    ArchitecturalTypeChecker, ValidationResult, ValidationIssue,
    Severity
)

__all__ = [
    "ArchitecturalTypeChecker", "ValidationResult", "ValidationIssue",
    "Severity",
]