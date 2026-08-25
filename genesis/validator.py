"""Genesis Validator — asserts candidate ISR₀ is faithful to requirements."""

from __future__ import annotations

from typing import Protocol

from isr.core.identity import compute_content_hash
from isr.core.invariants import ISRInvariantViolation, validate_invariants
from isr.core.revision import ISRRevision
from genesis.evidence import GenesisEvidence


class GenesisValidator(Protocol):
    def validate(
        self, candidate: ISRRevision, evidence: GenesisEvidence
    ) -> list[str]: ...


class ReferenceGenesisValidator:
    """Reference implementation: fail-closed, returns list of violations (empty = pass)."""

    def validate(
        self, candidate: ISRRevision, evidence: GenesisEvidence
    ) -> list[str]:
        violations: list[str] = []

        try:
            validate_invariants(candidate.graph)
        except ISRInvariantViolation as exc:
            violations.append(f"ADR-008 invariant violation: {exc}")

        expected_hash = compute_content_hash(
            candidate.schema_version, candidate.graph
        )
        if evidence.validation.content_hash != expected_hash:
            violations.append(
                f"content_hash mismatch: evidence={evidence.validation.content_hash[:16]}… "
                f"candidate={expected_hash[:16]}…"
            )

        if not evidence.validation.adr008_invariants_passed:
            violations.append("evidence.validation.adr008_invariants_passed is False")

        if evidence.coverage.uncovered:
            violations.append(
                f"uncovered requirements: {evidence.coverage.uncovered}"
            )

        return violations
