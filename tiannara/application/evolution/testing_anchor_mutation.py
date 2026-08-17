"""R2.10.3-H — the testing-anchor mutation operator (gene-level mutation).

``TestingAnchorOperator`` mutates the testing anchor gene class alone
(System.testing_anchors): add/remove/respecify/regrade/generate. It never
touches behavior, capability, requirement, acceptance-criterion, migration,
temporal, reliability, boundary, deployment, or entity genes.

Protection is R2.8.7's protected-evaluation-surface semantics generalized
into the ISR — ONE protection mechanism across primitives, not a parallel
security model. A PROTECTED anchor's removal or modification raises
ConstitutionalViolation (the same violation E's BoundaryOperator raises for
protected boundaries); EVOLVABLE removal restores the exact prior hash.
Elevating EVOLVABLE → PROTECTED is authorized; downgrading PROTECTED →
EVOLVABLE is a violation.

No operator here can attach a test implementation (file, function,
framework, fixture, marker, execution command), because the construct has
no field for one and the mechanism lint gates the semantic form.

Every mutation is attributed in the ledger as an R2.8.3 MEASUREMENT event.
The operator is deterministic: identical inputs produce identical candidates.
"""
from __future__ import annotations

import dataclasses
import json
from typing import Optional, Sequence

from constitutional_architecture.isr.model import (
    AnchorAuthority,
    ISR,
    ProtectionPolicy,
    TestingAnchor,
    TestingAnchorValidationError,
)
from constitutional_architecture.validators import ConstitutionalViolation

from .ledger import EventType, EvolutionEvent, EvolutionLedger, stable_isr_hash
from .mutation_operators import ISRDelta, MutationCandidate


class TestingAnchorOperator:
    """Mutates only the testing anchor gene class (System.testing_anchors)."""

    operator_id = "testing_anchor"

    def __init__(self, ledger: Optional[EvolutionLedger] = None) -> None:
        self._ledger = ledger

    # -- rebuild helpers ------------------------------------------------------

    @staticmethod
    def _replace_anchors(isr: ISR, anchors: Sequence[TestingAnchor]) -> ISR:
        return isr.with_system(
            dataclasses.replace(isr.system, testing_anchors=tuple(anchors))
        )

    @staticmethod
    def _candidate(
        isr: ISR,
        after: ISR,
        operation: str,
        subject_id: str,
    ) -> MutationCandidate:
        delta = ISRDelta(
            (
                json.dumps(
                    {
                        "operator": "testing_anchor",
                        "operation": operation,
                        "subject_id": subject_id,
                    },
                    sort_keys=True,
                ),
            )
        )
        return MutationCandidate(
            candidate_id=f"{TestingAnchorOperator.operator_id}:"
            f"{stable_isr_hash(after)[:12]}",
            operator_id=TestingAnchorOperator.operator_id,
            candidate_isr=after,
            parent_isr=isr,
            mutation_delta=delta,
            hypothesis=f"testing_anchor: {operation} '{subject_id}'",
        )

    # -- attribution ------------------------------------------------------------

    def _attest(
        self,
        before: ISR,
        after: ISR,
        operation: str,
        subject_id: str,
    ) -> None:
        if self._ledger is None:
            return
        event = EvolutionEvent(
            event_id="",
            evolution_id="r2.10.3-h",
            sequence=0,
            event_type=EventType.MEASUREMENT,
            subject_id=subject_id,
            isr_hash=stable_isr_hash(after),
            payload={
                "operator_id": self.operator_id,
                "operation": operation,
                "subject_id": subject_id,
                "isr_hash_before": stable_isr_hash(before),
                "isr_hash_after": stable_isr_hash(after),
            },
        )
        self._ledger.append_event(event, evolution_id="r2.10.3-h")

    # -- protection gate ----------------------------------------------------------

    @staticmethod
    def _guard_protected(anchor: TestingAnchor, operation: str) -> None:
        if anchor.protection_policy is ProtectionPolicy.PROTECTED:
            raise ConstitutionalViolation(
                f"anchor '{anchor.anchor_id}' is PROTECTED: {operation} is a "
                f"constitutional violation, not an edit"
            )

    # -- operations -----------------------------------------------------------------

    def add_anchor(
        self, isr: ISR, anchor: TestingAnchor
    ) -> MutationCandidate:
        """Declare one anchoring relationship — nothing else changes."""
        existing = {a.anchor_id for a in isr.system.testing_anchors}
        if anchor.anchor_id in existing:
            raise TestingAnchorValidationError(
                f"anchor '{anchor.anchor_id}' already declared"
            )
        after = self._replace_anchors(
            isr, isr.system.testing_anchors + (anchor,)
        )
        self._attest(isr, after, "add_anchor", anchor.anchor_id)
        return self._candidate(isr, after, "add_anchor", anchor.anchor_id)

    def remove_anchor(
        self, isr: ISR, *, anchor_id: str
    ) -> MutationCandidate:
        """Remove one anchor. PROTECTED anchors are constitutionally
        undetachable; EVOLVABLE removal restores the exact prior hash."""
        for anchor in isr.system.testing_anchors:
            if anchor.anchor_id == anchor_id:
                self._guard_protected(anchor, "removal")
                after = self._replace_anchors(
                    isr,
                    tuple(
                        a
                        for a in isr.system.testing_anchors
                        if a.anchor_id != anchor_id
                    ),
                )
                self._attest(isr, after, "remove_anchor", anchor_id)
                return self._candidate(isr, after, "remove_anchor", anchor_id)
        raise TestingAnchorValidationError(
            f"anchor '{anchor_id}' not found"
        )

    def respecify_anchor(
        self,
        isr: ISR,
        *,
        anchor_id: str,
        evidence_requirements: tuple[str, ...],
    ) -> MutationCandidate:
        """Respecify the evidence contract; every other dimension is untouched.

        Reference-by-identity, backwards: the subject genes this anchor
        references by id do NOT move.
        """
        for anchor in isr.system.testing_anchors:
            if anchor.anchor_id == anchor_id:
                self._guard_protected(anchor, "modification")
                edited = dataclasses.replace(
                    anchor, evidence_requirements=evidence_requirements
                )
                after = self._replace_anchors(
                    isr,
                    tuple(
                        edited if a.anchor_id == anchor_id else a
                        for a in isr.system.testing_anchors
                    ),
                )
                self._attest(isr, after, "respecify_anchor", anchor_id)
                return self._candidate(isr, after, "respecify_anchor", anchor_id)
        raise TestingAnchorValidationError(
            f"anchor '{anchor_id}' not found"
        )

    def regrade_anchor(
        self,
        isr: ISR,
        *,
        anchor_id: str,
        policy: ProtectionPolicy,
    ) -> MutationCandidate:
        """Change the protection grade. Elevation (EVOLVABLE → PROTECTED) is
        authorized; downgrade of a PROTECTED anchor is a violation."""
        for anchor in isr.system.testing_anchors:
            if anchor.anchor_id == anchor_id:
                if (
                    anchor.protection_policy is ProtectionPolicy.PROTECTED
                    and policy is ProtectionPolicy.EVOLVABLE
                ):
                    raise ConstitutionalViolation(
                        f"anchor '{anchor_id}' is PROTECTED: downgrading to "
                        f"EVOLVABLE is a constitutional violation"
                    )
                edited = dataclasses.replace(anchor, protection_policy=policy)
                after = self._replace_anchors(
                    isr,
                    tuple(
                        edited if a.anchor_id == anchor_id else a
                        for a in isr.system.testing_anchors
                    ),
                )
                self._attest(isr, after, "regrade_anchor", anchor_id)
                return self._candidate(isr, after, "regrade_anchor", anchor_id)
        raise TestingAnchorValidationError(
            f"anchor '{anchor_id}' not found"
        )

    # -- deterministic generation ---------------------------------------------------

    def generate(
        self,
        isr: ISR,
        *,
        seed: Optional[int] = None,
        population_size: int = 1,
    ) -> tuple[MutationCandidate, ...]:
        """Seed-replayable candidate generation over the testing anchor gene class.

        Deterministic by construction: candidates anchor the first
        ``population_size`` sorted workflows with a DERIVED EVOLVABLE anchor
        and a semantic evidence requirement — no randomness, ``seed``
        accepted for protocol compatibility and reproducibility attestation.
        """
        del seed
        candidates: list[MutationCandidate] = []
        workflow_ids = sorted(
            w.id for m in isr.system.modules for w in m.workflows
        )
        for i in range(min(len(workflow_ids), population_size)):
            anchor = TestingAnchor(
                anchor_id=f"anchor.{workflow_ids[i]}",
                subject_refs=(workflow_ids[i],),
                evidence_requirements=(
                    "the declared behavior must be demonstrated",),
                protection_policy=ProtectionPolicy.EVOLVABLE,
                authority=AnchorAuthority.DERIVED,
            )
            candidates.append(self.add_anchor(isr, anchor))
        return tuple(candidates)