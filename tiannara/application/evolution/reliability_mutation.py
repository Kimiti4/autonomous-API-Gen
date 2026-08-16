"""R2.10.3-D — the reliability mutation operator (gene-level mutation).

``ReliabilityOperator`` mutates the reliability gene class alone:
add/remove/set-degradation-policy/add-recovery-objective. It never touches
behavior, capability, migration, temporal, or entity genes — the
mutation-locality contract that makes ``reliability_requirements``
independently evolvable.

A requirement's gene is (failure modes, recovery objectives, degradation
policy, preservation invariants, dependency constraints) — required behavior
under failure, semantic declarations only. No operator here can attach a
mechanism (retry count, backoff, replica count, restart policy, probe,
queue name), because the construct has no field for one.

Every mutation is attributed in the ledger as an R2.8.3 MEASUREMENT event.
The operator is deterministic: identical inputs produce identical candidates.
"""
from __future__ import annotations

import dataclasses
import json
from typing import Optional, Sequence

from constitutional_architecture.isr.model import (
    FailureMode,
    ISR,
    RecoveryBehavior,
    RecoveryObjective,
    ReliabilityRequirement,
    ReliabilityValidationError,
)

from .ledger import EventType, EvolutionEvent, EvolutionLedger, stable_isr_hash
from .mutation_operators import ISRDelta, MutationCandidate


class ReliabilityOperator:
    """Mutates only the reliability gene class (System.reliability_requirements)."""

    operator_id = "reliability"

    def __init__(self, ledger: Optional[EvolutionLedger] = None) -> None:
        self._ledger = ledger

    # -- rebuild helpers ------------------------------------------------------

    @staticmethod
    def _replace_requirements(
        isr: ISR, requirements: Sequence[ReliabilityRequirement]
    ) -> ISR:
        return isr.with_system(
            dataclasses.replace(
                isr.system, reliability_requirements=tuple(requirements)
            )
        )

    @staticmethod
    def _candidate(
        isr: ISR,
        after: ISR,
        operation: str,
        requirement: ReliabilityRequirement,
    ) -> MutationCandidate:
        delta = ISRDelta(
            (
                json.dumps(
                    {
                        "operator": "reliability",
                        "operation": operation,
                        "requirement_id": requirement.requirement_id,
                        "target_refs": list(requirement.target_refs),
                        "failure_modes": [
                            mode.value for mode in requirement.failure_modes
                        ],
                    },
                    sort_keys=True,
                ),
            )
        )
        return MutationCandidate(
            candidate_id=f"{ReliabilityOperator.operator_id}:"
            f"{stable_isr_hash(after)[:12]}",
            operator_id=ReliabilityOperator.operator_id,
            candidate_isr=after,
            parent_isr=isr,
            mutation_delta=delta,
            hypothesis=f"reliability: {operation} '{requirement.requirement_id}'",
        )

    # -- attribution ------------------------------------------------------------

    def _attest(
        self,
        before: ISR,
        after: ISR,
        operation: str,
        requirement: ReliabilityRequirement,
    ) -> None:
        if self._ledger is None:
            return
        event = EvolutionEvent(
            event_id="",
            evolution_id="r2.10.3-d",
            sequence=0,
            event_type=EventType.MEASUREMENT,
            subject_id=requirement.requirement_id,
            isr_hash=stable_isr_hash(after),
            payload={
                "operator_id": self.operator_id,
                "operation": operation,
                "requirement_id": requirement.requirement_id,
                "target_refs": list(requirement.target_refs),
                "failure_modes": [mode.value for mode in requirement.failure_modes],
                "isr_hash_before": stable_isr_hash(before),
                "isr_hash_after": stable_isr_hash(after),
            },
        )
        self._ledger.append_event(event, evolution_id="r2.10.3-d")

    # -- operations -----------------------------------------------------------------

    def add_requirement(
        self, isr: ISR, requirement: ReliabilityRequirement
    ) -> MutationCandidate:
        """Declare one reliability requirement — nothing else changes."""
        existing = {
            r.requirement_id for r in isr.system.reliability_requirements
        }
        if requirement.requirement_id in existing:
            raise ReliabilityValidationError(
                f"reliability requirement '{requirement.requirement_id}' "
                f"already declared"
            )
        after = self._replace_requirements(
            isr, isr.system.reliability_requirements + (requirement,)
        )
        self._attest(isr, after, "add_requirement", requirement)
        return self._candidate(isr, after, "add_requirement", requirement)

    def remove_requirement(
        self, isr: ISR, *, requirement_id: str
    ) -> MutationCandidate:
        """Remove one requirement — the protected targets are untouched."""
        for requirement in isr.system.reliability_requirements:
            if requirement.requirement_id == requirement_id:
                after = self._replace_requirements(
                    isr,
                    tuple(
                        r
                        for r in isr.system.reliability_requirements
                        if r.requirement_id != requirement_id
                    ),
                )
                self._attest(isr, after, "remove_requirement", requirement)
                return self._candidate(isr, after, "remove_requirement", requirement)
        raise ReliabilityValidationError(
            f"reliability requirement '{requirement_id}' not found"
        )

    def set_degradation_policy(
        self,
        isr: ISR,
        *,
        requirement_id: str,
        policy: object,
    ) -> MutationCandidate:
        """Respecify acceptable degradation STATE; every other dimension is untouched."""
        for requirement in isr.system.reliability_requirements:
            if requirement.requirement_id == requirement_id:
                edited = dataclasses.replace(requirement, degradation_policy=policy)
                after = self._replace_requirements(
                    isr,
                    tuple(
                        edited if r.requirement_id == requirement_id else r
                        for r in isr.system.reliability_requirements
                    ),
                )
                self._attest(isr, after, "set_degradation_policy", edited)
                return self._candidate(isr, after, "set_degradation_policy", edited)
        raise ReliabilityValidationError(
            f"reliability requirement '{requirement_id}' not found"
        )

    def add_recovery_objective(
        self,
        isr: ISR,
        *,
        requirement_id: str,
        objective: RecoveryObjective,
    ) -> MutationCandidate:
        """Declare required recovery behavior for one failure mode."""
        for requirement in isr.system.reliability_requirements:
            if requirement.requirement_id == requirement_id:
                if any(
                    o.failure_mode == objective.failure_mode
                    for o in requirement.recovery_objectives
                ):
                    raise ReliabilityValidationError(
                        f"recovery objective for failure mode "
                        f"'{objective.failure_mode.value}' already declared in "
                        f"'{requirement_id}'"
                    )
                edited = dataclasses.replace(
                    requirement,
                    recovery_objectives=requirement.recovery_objectives
                    + (objective,),
                )
                after = self._replace_requirements(
                    isr,
                    tuple(
                        edited if r.requirement_id == requirement_id else r
                        for r in isr.system.reliability_requirements
                    ),
                )
                self._attest(isr, after, "add_recovery_objective", edited)
                return self._candidate(
                    isr, after, "add_recovery_objective", edited
                )
        raise ReliabilityValidationError(
            f"reliability requirement '{requirement_id}' not found"
        )

    # -- deterministic generation ---------------------------------------------------

    def generate(
        self,
        isr: ISR,
        *,
        seed: Optional[int] = None,
        population_size: int = 1,
    ) -> tuple[MutationCandidate, ...]:
        """Seed-replayable candidate generation over the reliability gene class.

        Deterministic by construction: candidates protect the first
        ``population_size`` sorted business capabilities against transient
        dependency failure with eventual recovery and a 5000ms semantic
        deadline — no randomness, ``seed`` accepted for protocol compatibility
        and reproducibility attestation.
        """
        del seed
        candidates: list[MutationCandidate] = []
        capabilities = sorted(
            isr.system.business_capabilities, key=lambda c: c.capability_id
        )
        for i in range(min(len(capabilities), population_size)):
            capability = capabilities[i]
            requirement = ReliabilityRequirement(
                requirement_id=f"rel.{capability.capability_id}",
                target_refs=(capability.capability_id,),
                failure_modes=(FailureMode.TRANSIENT_DEPENDENCY_FAILURE,),
                recovery_objectives=(
                    RecoveryObjective(
                        failure_mode=FailureMode.TRANSIENT_DEPENDENCY_FAILURE,
                        required_behavior=RecoveryBehavior.EVENTUAL_RECOVERY,
                        max_recovery_duration_ms=5000,
                    ),
                ),
                degradation_policy=None,
                preservation_invariants=(f"{capability.capability_id} coherent",),
            )
            candidates.append(self.add_requirement(isr, requirement))
        return tuple(candidates)