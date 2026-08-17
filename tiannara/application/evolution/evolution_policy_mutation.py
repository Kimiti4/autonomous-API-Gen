"""R2.10.3-J — the evolution-policy mutation operator (gene-level mutation).

``EvolutionPolicyOperator`` mutates the evolution-policy gene classes alone
(System.evolution_objectives, System.protected_regions,
System.evolution_policies): add/remove/respecify objectives, regions, and
policies, plus deterministic generation. It never touches behavior,
capability, requirement, acceptance-criterion, migration, temporal,
reliability, boundary, deployment, testing-anchor, documentation, or entity
genes.

J is the constitutional declaration of evolution authority. This operator
therefore can NEVER create or import a ConstitutionalAuthorization — the
authorization seam lives in constitutional_architecture.governance, outside
the evolution package (module-boundary test). Protected regions declared
here are enforced by EvolutionProtectionEvaluator as a feasibility gate;
IMMUTABLE and PRESERVATION regions are ordinary mutations of the policy
itself, while CONSTITUTIONAL-region CHANGES to the protected subjects are
governance-authorization matters handled outside this operator entirely.

Every mutation is attributed in the ledger as an R2.8.3 MEASUREMENT event.
The operator is deterministic: identical inputs produce identical candidates.
"""
from __future__ import annotations

import dataclasses
import json
from typing import Optional, Sequence

from constitutional_architecture.isr.model import (
    EvolutionObjective,
    EvolutionPolicy,
    EvolutionPolicyValidationError,
    ISR,
    ObjectiveDimension,
    ObjectiveDirection,
    ObjectiveTier,
    ProtectedRegion,
    ProtectionKind,
)

from .ledger import EventType, EvolutionEvent, EvolutionLedger, stable_isr_hash
from .mutation_operators import ISRDelta, MutationCandidate


class EvolutionPolicyOperator:
    """Mutates only the evolution-policy gene classes."""

    operator_id = "evolution_policy"

    def __init__(self, ledger: Optional[EvolutionLedger] = None) -> None:
        self._ledger = ledger

    # -- rebuild helpers ------------------------------------------------------

    @staticmethod
    def _replace_objectives(
        isr: ISR, objectives: Sequence[EvolutionObjective]
    ) -> ISR:
        return isr.with_system(
            dataclasses.replace(isr.system, evolution_objectives=tuple(objectives))
        )

    @staticmethod
    def _replace_regions(
        isr: ISR, regions: Sequence[ProtectedRegion]
    ) -> ISR:
        return isr.with_system(
            dataclasses.replace(isr.system, protected_regions=tuple(regions))
        )

    @staticmethod
    def _replace_policies(
        isr: ISR, policies: Sequence[EvolutionPolicy]
    ) -> ISR:
        return isr.with_system(
            dataclasses.replace(isr.system, evolution_policies=tuple(policies))
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
                        "operator": "evolution_policy",
                        "operation": operation,
                        "subject_id": subject_id,
                    },
                    sort_keys=True,
                ),
            )
        )
        return MutationCandidate(
            candidate_id=f"{EvolutionPolicyOperator.operator_id}:"
            f"{stable_isr_hash(after)[:12]}",
            operator_id=EvolutionPolicyOperator.operator_id,
            candidate_isr=after,
            parent_isr=isr,
            mutation_delta=delta,
            hypothesis=f"evolution_policy: {operation} '{subject_id}'",
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
            evolution_id="r2.10.3-j",
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
        self._ledger.append_event(event, evolution_id="r2.10.3-j")

    # -- objectives -----------------------------------------------------------------

    def add_objective(
        self, isr: ISR, objective: EvolutionObjective
    ) -> MutationCandidate:
        existing = {o.objective_id for o in isr.system.evolution_objectives}
        if objective.objective_id in existing:
            raise EvolutionPolicyValidationError(
                f"objective '{objective.objective_id}' already declared"
            )
        after = self._replace_objectives(
            isr, isr.system.evolution_objectives + (objective,)
        )
        self._attest(isr, after, "add_objective", objective.objective_id)
        return self._candidate(isr, after, "add_objective", objective.objective_id)

    def remove_objective(
        self, isr: ISR, *, objective_id: str
    ) -> MutationCandidate:
        for objective in isr.system.evolution_objectives:
            if objective.objective_id == objective_id:
                after = self._replace_objectives(
                    isr,
                    tuple(
                        o
                        for o in isr.system.evolution_objectives
                        if o.objective_id != objective_id
                    ),
                )
                self._attest(isr, after, "remove_objective", objective_id)
                return self._candidate(isr, after, "remove_objective", objective_id)
        raise EvolutionPolicyValidationError(
            f"objective '{objective_id}' not found"
        )

    def respecify_objective(
        self,
        isr: ISR,
        *,
        objective_id: str,
        dimension: Optional[ObjectiveDimension] = None,
        direction: Optional[ObjectiveDirection] = None,
        tier: Optional[ObjectiveTier] = None,
        priority: Optional[int] = None,
        weight: Optional[float] = None,
        subject_refs: Optional[tuple[str, ...]] = None,
    ) -> MutationCandidate:
        """Respecify one objective; every unset dimension is untouched.
        Reference-by-identity, backwards: the subject genes this objective
        references by id do NOT move."""
        for objective in isr.system.evolution_objectives:
            if objective.objective_id == objective_id:
                edited = dataclasses.replace(
                    objective,
                    dimension=dimension if dimension is not None else objective.dimension,
                    direction=direction if direction is not None else objective.direction,
                    tier=tier if tier is not None else objective.tier,
                    priority=priority if priority is not None else objective.priority,
                    weight=weight if weight is not None else objective.weight,
                    subject_refs=(
                        subject_refs if subject_refs is not None else objective.subject_refs
                    ),
                )
                after = self._replace_objectives(
                    isr,
                    tuple(
                        edited if o.objective_id == objective_id else o
                        for o in isr.system.evolution_objectives
                    ),
                )
                self._attest(isr, after, "respecify_objective", objective_id)
                return self._candidate(isr, after, "respecify_objective", objective_id)
        raise EvolutionPolicyValidationError(
            f"objective '{objective_id}' not found"
        )

    # -- protected regions ------------------------------------------------------------

    def add_region(
        self, isr: ISR, region: ProtectedRegion
    ) -> MutationCandidate:
        existing = {r.region_id for r in isr.system.protected_regions}
        if region.region_id in existing:
            raise EvolutionPolicyValidationError(
                f"region '{region.region_id}' already declared"
            )
        after = self._replace_regions(
            isr, isr.system.protected_regions + (region,)
        )
        self._attest(isr, after, "add_region", region.region_id)
        return self._candidate(isr, after, "add_region", region.region_id)

    def remove_region(
        self, isr: ISR, *, region_id: str
    ) -> MutationCandidate:
        for region in isr.system.protected_regions:
            if region.region_id == region_id:
                after = self._replace_regions(
                    isr,
                    tuple(
                        r
                        for r in isr.system.protected_regions
                        if r.region_id != region_id
                    ),
                )
                self._attest(isr, after, "remove_region", region_id)
                return self._candidate(isr, after, "remove_region", region_id)
        raise EvolutionPolicyValidationError(
            f"region '{region_id}' not found"
        )

    def respecify_region(
        self,
        isr: ISR,
        *,
        region_id: str,
        protection_kind: Optional[ProtectionKind] = None,
        subject_refs: Optional[tuple[str, ...]] = None,
        invariants: Optional[tuple] = None,
    ) -> MutationCandidate:
        """Respecify one protected region; every unset dimension is untouched.
        Declares which semantic identities participate in the protected
        evolution policy — never re-implements E's or H's mechanics."""
        for region in isr.system.protected_regions:
            if region.region_id == region_id:
                edited = dataclasses.replace(
                    region,
                    protection_kind=(
                        protection_kind
                        if protection_kind is not None
                        else region.protection_kind
                    ),
                    subject_refs=(
                        subject_refs if subject_refs is not None else region.subject_refs
                    ),
                    invariants=(
                        invariants if invariants is not None else region.invariants
                    ),
                )
                after = self._replace_regions(
                    isr,
                    tuple(
                        edited if r.region_id == region_id else r
                        for r in isr.system.protected_regions
                    ),
                )
                self._attest(isr, after, "respecify_region", region_id)
                return self._candidate(isr, after, "respecify_region", region_id)
        raise EvolutionPolicyValidationError(
            f"region '{region_id}' not found"
        )

    # -- policies ------------------------------------------------------------------

    def add_policy(
        self, isr: ISR, policy: EvolutionPolicy
    ) -> MutationCandidate:
        existing = {p.policy_id for p in isr.system.evolution_policies}
        if policy.policy_id in existing:
            raise EvolutionPolicyValidationError(
                f"policy '{policy.policy_id}' already declared"
            )
        after = self._replace_policies(
            isr, isr.system.evolution_policies + (policy,)
        )
        self._attest(isr, after, "add_policy", policy.policy_id)
        return self._candidate(isr, after, "add_policy", policy.policy_id)

    def remove_policy(
        self, isr: ISR, *, policy_id: str
    ) -> MutationCandidate:
        for policy in isr.system.evolution_policies:
            if policy.policy_id == policy_id:
                after = self._replace_policies(
                    isr,
                    tuple(
                        p
                        for p in isr.system.evolution_policies
                        if p.policy_id != policy_id
                    ),
                )
                self._attest(isr, after, "remove_policy", policy_id)
                return self._candidate(isr, after, "remove_policy", policy_id)
        raise EvolutionPolicyValidationError(
            f"policy '{policy_id}' not found"
        )

    def respecify_policy(
        self,
        isr: ISR,
        *,
        policy_id: str,
        objective_refs: Optional[tuple[str, ...]] = None,
        protected_region_refs: Optional[tuple[str, ...]] = None,
        selection_constraints: Optional[tuple[str, ...]] = None,
    ) -> MutationCandidate:
        """Respecify one policy; every unset dimension is untouched."""
        for policy in isr.system.evolution_policies:
            if policy.policy_id == policy_id:
                edited = dataclasses.replace(
                    policy,
                    objective_refs=(
                        objective_refs
                        if objective_refs is not None
                        else policy.objective_refs
                    ),
                    protected_region_refs=(
                        protected_region_refs
                        if protected_region_refs is not None
                        else policy.protected_region_refs
                    ),
                    selection_constraints=(
                        selection_constraints
                        if selection_constraints is not None
                        else policy.selection_constraints
                    ),
                )
                after = self._replace_policies(
                    isr,
                    tuple(
                        edited if p.policy_id == policy_id else p
                        for p in isr.system.evolution_policies
                    ),
                )
                self._attest(isr, after, "respecify_policy", policy_id)
                return self._candidate(isr, after, "respecify_policy", policy_id)
        raise EvolutionPolicyValidationError(
            f"policy '{policy_id}' not found"
        )

    # -- deterministic generation ---------------------------------------------------

    def generate(
        self,
        isr: ISR,
        *,
        seed: Optional[int] = None,
        population_size: int = 1,
    ) -> tuple[MutationCandidate, ...]:
        """Seed-replayable candidate generation over the evolution-policy
        gene classes.

        Deterministic by construction: candidates protect the first
        ``population_size`` sorted workflows as an IMMUTABLE region governed
        by a RELIABILITY-maximizing objective and a referencing policy — no
        randomness, ``seed`` accepted for protocol compatibility and
        reproducibility attestation.
        """
        del seed
        candidates: list[MutationCandidate] = []
        workflow_ids = sorted(
            w.id for m in isr.system.modules for w in m.workflows
        )
        for i in range(min(len(workflow_ids), population_size)):
            objective = EvolutionObjective(
                objective_id=f"obj.{workflow_ids[i]}",
                dimension=ObjectiveDimension.RELIABILITY,
                direction=ObjectiveDirection.MAXIMIZE,
                tier=ObjectiveTier.OPTIMIZATION,
                priority=0,
                weight=1.0,
                subject_refs=(workflow_ids[i],),
            )
            region = ProtectedRegion(
                region_id=f"region.{workflow_ids[i]}",
                subject_refs=(workflow_ids[i],),
                protection_kind=ProtectionKind.IMMUTABLE,
            )
            with_objective = self.add_objective(isr, objective)
            with_region = self.add_region(with_objective.candidate_isr, region)
            policy = EvolutionPolicy(
                policy_id=f"policy.{workflow_ids[i]}",
                objective_refs=(objective.objective_id,),
                protected_region_refs=(region.region_id,),
                selection_constraints=(
                    "no candidate may sacrifice the declared reliability",),
            )
            with_policy = self.add_policy(with_region.candidate_isr, policy)
            candidates.append(with_policy)
        return tuple(candidates)