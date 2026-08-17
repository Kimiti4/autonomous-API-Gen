"""R2.10.3-F — the requirement mutation operator (gene-level mutation).

``RequirementOperator`` mutates the requirement gene classes alone
(System.requirements + System.acceptance_criteria): add/remove/set-statement/
add-criterion/assign-criterion/link-capability. It never touches behavior,
capability, migration, temporal, reliability, boundary, or entity genes —
except for ``link_capability``, which adds an EXPLICITLY DECLARED
cross-reference to a capability's reserved ``requirement_refs`` (the
declared link moves the capability gene by design — the asymmetry proven in
the suite).

A requirement's gene is (statement, targets, acceptance refs, constraint
refs) — a semantic obligation, never an implementation task. No operator
here can attach a test reference (pytest file, runner, assertion), because
the construct has no field for one.

Every mutation is attributed in the ledger as an R2.8.3 MEASUREMENT event.
The operator is deterministic: identical inputs produce identical candidates.
"""
from __future__ import annotations

import dataclasses
import json
from typing import Optional, Sequence

from constitutional_architecture.isr.model import (
    AcceptanceCriterion,
    ISR,
    ObligationKind,
    Requirement,
    RequirementValidationError,
)

from .ledger import EventType, EvolutionEvent, EvolutionLedger, stable_isr_hash
from .mutation_operators import ISRDelta, MutationCandidate


class RequirementOperator:
    """Mutates only the requirement gene classes (System.requirements,
    System.acceptance_criteria) plus the declared capability link."""

    operator_id = "requirement"

    def __init__(self, ledger: Optional[EvolutionLedger] = None) -> None:
        self._ledger = ledger

    # -- rebuild helpers ------------------------------------------------------

    @staticmethod
    def _replace_requirements(
        isr: ISR, requirements: Sequence[Requirement]
    ) -> ISR:
        return isr.with_system(
            dataclasses.replace(isr.system, requirements=tuple(requirements))
        )

    @staticmethod
    def _replace_criteria(
        isr: ISR, criteria: Sequence[AcceptanceCriterion]
    ) -> ISR:
        return isr.with_system(
            dataclasses.replace(isr.system, acceptance_criteria=tuple(criteria))
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
                        "operator": "requirement",
                        "operation": operation,
                        "subject_id": subject_id,
                    },
                    sort_keys=True,
                ),
            )
        )
        return MutationCandidate(
            candidate_id=f"{RequirementOperator.operator_id}:"
            f"{stable_isr_hash(after)[:12]}",
            operator_id=RequirementOperator.operator_id,
            candidate_isr=after,
            parent_isr=isr,
            mutation_delta=delta,
            hypothesis=f"requirement: {operation} '{subject_id}'",
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
            evolution_id="r2.10.3-f",
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
        self._ledger.append_event(event, evolution_id="r2.10.3-f")

    # -- operations -----------------------------------------------------------------

    def add_requirement(
        self, isr: ISR, requirement: Requirement
    ) -> MutationCandidate:
        """Declare one semantic obligation — nothing else changes."""
        existing = {r.requirement_id for r in isr.system.requirements}
        if requirement.requirement_id in existing:
            raise RequirementValidationError(
                f"requirement '{requirement.requirement_id}' already declared"
            )
        after = self._replace_requirements(
            isr, isr.system.requirements + (requirement,)
        )
        self._attest(isr, after, "add_requirement", requirement.requirement_id)
        return self._candidate(isr, after, "add_requirement", requirement.requirement_id)

    def remove_requirement(
        self, isr: ISR, *, requirement_id: str
    ) -> MutationCandidate:
        """Remove one obligation — the targeted capabilities are untouched."""
        for requirement in isr.system.requirements:
            if requirement.requirement_id == requirement_id:
                after = self._replace_requirements(
                    isr,
                    tuple(
                        r
                        for r in isr.system.requirements
                        if r.requirement_id != requirement_id
                    ),
                )
                self._attest(isr, after, "remove_requirement", requirement_id)
                return self._candidate(isr, after, "remove_requirement", requirement_id)
        raise RequirementValidationError(
            f"requirement '{requirement_id}' not found"
        )

    def set_statement(
        self, isr: ISR, *, requirement_id: str, statement: str
    ) -> MutationCandidate:
        """Respecify the obligation; every other dimension is untouched.

        Reference-by-identity: the capability that references this
        requirement by id does NOT move (proven in the suite).
        """
        for requirement in isr.system.requirements:
            if requirement.requirement_id == requirement_id:
                edited = dataclasses.replace(requirement, statement=statement)
                after = self._replace_requirements(
                    isr,
                    tuple(
                        edited if r.requirement_id == requirement_id else r
                        for r in isr.system.requirements
                    ),
                )
                self._attest(isr, after, "set_statement", requirement_id)
                return self._candidate(isr, after, "set_statement", requirement_id)
        raise RequirementValidationError(
            f"requirement '{requirement_id}' not found"
        )

    def add_criterion(
        self, isr: ISR, criterion: AcceptanceCriterion
    ) -> MutationCandidate:
        """Declare one acceptance criterion — nothing else changes."""
        existing = {c.criterion_id for c in isr.system.acceptance_criteria}
        if criterion.criterion_id in existing:
            raise RequirementValidationError(
                f"acceptance criterion '{criterion.criterion_id}' already declared"
            )
        after = self._replace_criteria(
            isr, isr.system.acceptance_criteria + (criterion,)
        )
        self._attest(isr, after, "add_criterion", criterion.criterion_id)
        return self._candidate(isr, after, "add_criterion", criterion.criterion_id)

    def assign_criterion(
        self, isr: ISR, *, requirement_id: str, criterion_id: str
    ) -> MutationCandidate:
        """Bind an acceptance criterion to an obligation (identity only)."""
        for requirement in isr.system.requirements:
            if requirement.requirement_id == requirement_id:
                if criterion_id in requirement.acceptance_refs:
                    raise RequirementValidationError(
                        f"criterion '{criterion_id}' already assigned to "
                        f"'{requirement_id}'"
                    )
                edited = dataclasses.replace(
                    requirement,
                    acceptance_refs=requirement.acceptance_refs + (criterion_id,),
                )
                after = self._replace_requirements(
                    isr,
                    tuple(
                        edited if r.requirement_id == requirement_id else r
                        for r in isr.system.requirements
                    ),
                )
                self._attest(isr, after, "assign_criterion", requirement_id)
                return self._candidate(isr, after, "assign_criterion", requirement_id)
        raise RequirementValidationError(
            f"requirement '{requirement_id}' not found"
        )

    def link_capability(
        self, isr: ISR, *, requirement_id: str, capability_id: str
    ) -> MutationCandidate:
        """Declare the capability -> requirement link explicitly.

        This is the declared cross-reference that makes traceability real:
        it mutates the CAPABILITY gene (its requirement_refs), which is the
        intended asymmetry — an explicitly declared link moves the capability,
        while the requirement's own content evolution never does.
        """
        if requirement_id not in {r.requirement_id for r in isr.system.requirements}:
            raise RequirementValidationError(
                f"requirement '{requirement_id}' not found"
            )
        capabilities = []
        found = False
        for capability in isr.system.business_capabilities:
            if capability.capability_id == capability_id:
                found = True
                if requirement_id in capability.requirement_refs:
                    raise RequirementValidationError(
                        f"requirement '{requirement_id}' already linked to "
                        f"capability '{capability_id}'"
                    )
                capability = dataclasses.replace(
                    capability,
                    requirement_refs=capability.requirement_refs
                    + (requirement_id,),
                )
            capabilities.append(capability)
        if not found:
            raise RequirementValidationError(
                f"capability '{capability_id}' not found"
            )
        after = isr.with_system(
            dataclasses.replace(
                isr.system, business_capabilities=tuple(capabilities)
            )
        )
        self._attest(isr, after, "link_capability", requirement_id)
        return self._candidate(isr, after, "link_capability", requirement_id)

    # -- deterministic generation ---------------------------------------------------

    def generate(
        self,
        isr: ISR,
        *,
        seed: Optional[int] = None,
        population_size: int = 1,
    ) -> tuple[MutationCandidate, ...]:
        """Seed-replayable candidate generation over the requirement gene class.

        Deterministic by construction: candidates declare an ordering
        obligation over the first ``population_size`` sorted capabilities,
        each with an INVARIANT acceptance criterion — no randomness, ``seed``
        accepted for protocol compatibility and reproducibility attestation.
        """
        del seed
        candidates: list[MutationCandidate] = []
        capabilities = sorted(
            isr.system.business_capabilities, key=lambda c: c.capability_id
        )
        for i in range(min(len(capabilities), population_size)):
            capability = capabilities[i]
            criterion = AcceptanceCriterion(
                criterion_id=f"crit.{capability.capability_id}",
                obligation=f"{capability.capability_id} remains coherent",
                kind=ObligationKind.INVARIANT,
                subject_refs=(capability.capability_id,),
            )
            requirement = Requirement(
                requirement_id=f"req.{capability.capability_id}",
                statement=f"{capability.capability_id} must complete",
                target_refs=(capability.capability_id,),
                acceptance_refs=(criterion.criterion_id,),
            )
            candidates.append(self.add_criterion(isr, criterion))
            candidates.append(self.add_requirement(isr, requirement))
        return tuple(candidates)