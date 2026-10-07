"""Bucket 3.10 — architecture-level non-functional/security reasoning.

This module evaluates governed architecture candidates against explicit
constraints before admission. It is intentionally read-only and never claims
global optimality.

Mandatory constraints fail closed. Soft objectives are reported as measured
scores; they do not override a violated mandatory constraint.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Iterable, Literal

ConstraintKind = Literal[
    "security", "privacy", "performance", "operability", "cost", "complexity"
]
Severity = Literal["mandatory", "advisory"]
Direction = Literal["max", "min"]

_VALID_KINDS = {
    "security", "privacy", "performance", "operability", "cost", "complexity"
}
_VALID_SEVERITIES = {"mandatory", "advisory"}
_VALID_DIRECTIONS = {"max", "min"}


@dataclass(frozen=True)
class NFRConstraint:
    constraint_id: str
    kind: ConstraintKind
    statement: str
    threshold: float
    severity: Severity = "mandatory"
    direction: Direction = "min"

    def __post_init__(self) -> None:
        if not self.constraint_id.strip() or not self.statement.strip():
            raise ValueError("constraint-id-and-statement-required")
        if self.kind not in _VALID_KINDS:
            raise ValueError("invalid-constraint-kind")
        if self.severity not in _VALID_SEVERITIES:
            raise ValueError("invalid-constraint-severity")
        if self.direction not in _VALID_DIRECTIONS:
            raise ValueError("invalid-constraint-direction")


@dataclass(frozen=True)
class NFRMeasurement:
    constraint_id: str
    value: float
    evidence_id: str
    current: bool = True

    def __post_init__(self) -> None:
        if not self.constraint_id.strip() or not self.evidence_id.strip():
            raise ValueError("measurement-ids-required")


@dataclass(frozen=True)
class NFRAssessment:
    candidate_id: str
    satisfied_constraint_ids: tuple[str, ...]
    violated_constraint_ids: tuple[str, ...]
    insufficient_evidence_ids: tuple[str, ...]
    advisory_constraint_ids: tuple[str, ...]
    admissible: bool
    digest: str


class NFRArchitectureEngine:
    """Assess one candidate against explicit NFR/security constraints."""

    def __init__(
        self,
        *,
        project_id: str,
        constraints: Iterable[NFRConstraint] = (),
    ) -> None:
        if not project_id.strip():
            raise ValueError("project-id-required")
        self.project_id = project_id
        self._constraints: dict[str, NFRConstraint] = {}
        for constraint in constraints:
            self.add_constraint(constraint)

    def add_constraint(self, constraint: NFRConstraint) -> None:
        if constraint.constraint_id in self._constraints:
            raise ValueError("duplicate-constraint-id")
        self._constraints[constraint.constraint_id] = constraint

    def assess(
        self,
        candidate_id: str,
        measurements: Iterable[NFRMeasurement],
    ) -> NFRAssessment:
        if not candidate_id.strip():
            raise ValueError("candidate-id-required")

        supplied: dict[str, NFRMeasurement] = {}
        for measurement in measurements:
            if measurement.constraint_id in supplied:
                raise ValueError("duplicate-measurement")
            supplied[measurement.constraint_id] = measurement

        satisfied: list[str] = []
        violated: list[str] = []
        insufficient: list[str] = []
        advisory: list[str] = []

        for constraint_id in sorted(self._constraints):
            constraint = self._constraints[constraint_id]
            measurement = supplied.get(constraint_id)
            if constraint.severity == "advisory":
                advisory.append(constraint_id)
                continue
            if measurement is None or not measurement.current:
                insufficient.append(constraint_id)
                continue

            if constraint.direction == "min":
                passes = measurement.value >= constraint.threshold
            else:
                passes = measurement.value <= constraint.threshold

            if passes:
                satisfied.append(constraint_id)
            else:
                violated.append(constraint_id)

        mandatory_ids = {
            constraint_id
            for constraint_id, constraint in self._constraints.items()
            if constraint.severity == "mandatory"
        }
        admissible = (
            not (mandatory_ids & set(violated))
            and not (mandatory_ids & set(insufficient))
        )

        payload = {
            "schema_version": "esap.nfr-architecture.v1",
            "project_id": self.project_id,
            "candidate_id": candidate_id,
            "satisfied": tuple(satisfied),
            "violated": tuple(violated),
            "insufficient": tuple(insufficient),
            "advisory": tuple(advisory),
        }
        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

        return NFRAssessment(
            candidate_id=candidate_id,
            satisfied_constraint_ids=tuple(satisfied),
            violated_constraint_ids=tuple(violated),
            insufficient_evidence_ids=tuple(insufficient),
            advisory_constraint_ids=tuple(advisory),
            admissible=admissible,
            digest=digest,
        )
