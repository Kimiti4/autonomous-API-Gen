"""R2.10.3-G — the deployment mutation operator (gene-level mutation).

``DeploymentOperator`` mutates the deployment intent gene class alone
(System.deployment_intents): add/remove/set-rollout-strategy/set-health-
requirements/generate. It never touches behavior, capability, migration,
temporal, reliability, boundary, requirement, or entity genes — deployment
is a lifecycle gene over the architecture, composing by reference only.

No operator here can attach a realization (Kubernetes manifest, replica
count, CI/CD pipeline), because the construct has no field for one, and the
mechanism lint gates the semantic form.

Every mutation is attributed in the ledger as an R2.8.3 MEASUREMENT event.
The operator is deterministic: identical inputs produce identical candidates.
"""
from __future__ import annotations

import dataclasses
import json
from typing import Optional, Sequence

from constitutional_architecture.isr.model import (
    DeploymentIntent,
    DeploymentValidationError,
    ISR,
    RolloutStrategy,
)

from .ledger import EventType, EvolutionEvent, EvolutionLedger, stable_isr_hash
from .mutation_operators import ISRDelta, MutationCandidate


class DeploymentOperator:
    """Mutates only the deployment intent gene class (System.deployment_intents)."""

    operator_id = "deployment"

    def __init__(self, ledger: Optional[EvolutionLedger] = None) -> None:
        self._ledger = ledger

    # -- rebuild helpers ------------------------------------------------------

    @staticmethod
    def _replace_intents(isr: ISR, intents: Sequence[DeploymentIntent]) -> ISR:
        return isr.with_system(
            dataclasses.replace(isr.system, deployment_intents=tuple(intents))
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
                        "operator": "deployment",
                        "operation": operation,
                        "subject_id": subject_id,
                    },
                    sort_keys=True,
                ),
            )
        )
        return MutationCandidate(
            candidate_id=f"{DeploymentOperator.operator_id}:"
            f"{stable_isr_hash(after)[:12]}",
            operator_id=DeploymentOperator.operator_id,
            candidate_isr=after,
            parent_isr=isr,
            mutation_delta=delta,
            hypothesis=f"deployment: {operation} '{subject_id}'",
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
            evolution_id="r2.10.3-g",
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
        self._ledger.append_event(event, evolution_id="r2.10.3-g")

    # -- operations -----------------------------------------------------------------

    def add_intent(
        self, isr: ISR, intent: DeploymentIntent
    ) -> MutationCandidate:
        """Declare one lifecycle intent — nothing else changes."""
        existing = {i.deployment_id for i in isr.system.deployment_intents}
        if intent.deployment_id in existing:
            raise DeploymentValidationError(
                f"deployment '{intent.deployment_id}' already declared"
            )
        after = self._replace_intents(
            isr, isr.system.deployment_intents + (intent,)
        )
        self._attest(isr, after, "add_intent", intent.deployment_id)
        return self._candidate(isr, after, "add_intent", intent.deployment_id)

    def remove_intent(
        self, isr: ISR, *, deployment_id: str
    ) -> MutationCandidate:
        """Remove one lifecycle intent — the targeted genes are untouched."""
        for intent in isr.system.deployment_intents:
            if intent.deployment_id == deployment_id:
                after = self._replace_intents(
                    isr,
                    tuple(
                        i
                        for i in isr.system.deployment_intents
                        if i.deployment_id != deployment_id
                    ),
                )
                self._attest(isr, after, "remove_intent", deployment_id)
                return self._candidate(isr, after, "remove_intent", deployment_id)
        raise DeploymentValidationError(
            f"deployment '{deployment_id}' not found"
        )

    def set_rollout_strategy(
        self,
        isr: ISR,
        *,
        deployment_id: str,
        strategy: RolloutStrategy,
    ) -> MutationCandidate:
        """Respecify the rollout strategy; every other dimension is untouched.

        Reference-by-identity, backwards: the boundary/module genes this
        deployment targets by id do NOT move (the no-backward-leak proof).
        """
        for intent in isr.system.deployment_intents:
            if intent.deployment_id == deployment_id:
                edited = dataclasses.replace(intent, rollout_strategy=strategy)
                after = self._replace_intents(
                    isr,
                    tuple(
                        edited if i.deployment_id == deployment_id else i
                        for i in isr.system.deployment_intents
                    ),
                )
                self._attest(isr, after, "set_rollout_strategy", deployment_id)
                return self._candidate(
                    isr, after, "set_rollout_strategy", deployment_id
                )
        raise DeploymentValidationError(
            f"deployment '{deployment_id}' not found"
        )

    def set_health_requirements(
        self,
        isr: ISR,
        *,
        deployment_id: str,
        health_requirements: tuple[str, ...],
    ) -> MutationCandidate:
        """Respecify the health contract; every other dimension is untouched."""
        for intent in isr.system.deployment_intents:
            if intent.deployment_id == deployment_id:
                edited = dataclasses.replace(
                    intent, health_requirements=health_requirements
                )
                after = self._replace_intents(
                    isr,
                    tuple(
                        edited if i.deployment_id == deployment_id else i
                        for i in isr.system.deployment_intents
                    ),
                )
                self._attest(isr, after, "set_health_requirements", deployment_id)
                return self._candidate(
                    isr, after, "set_health_requirements", deployment_id
                )
        raise DeploymentValidationError(
            f"deployment '{deployment_id}' not found"
        )

    # -- deterministic generation ---------------------------------------------------

    def generate(
        self,
        isr: ISR,
        *,
        seed: Optional[int] = None,
        population_size: int = 1,
    ) -> tuple[MutationCandidate, ...]:
        """Seed-replayable candidate generation over the deployment intent gene class.

        Deterministic by construction: candidates declare a PROGRESSIVE
        rollout over the first ``population_size`` sorted modules, each with
        a rollback contract restoring its own target — no randomness,
        ``seed`` accepted for protocol compatibility and reproducibility
        attestation.
        """
        del seed
        candidates: list[MutationCandidate] = []
        modules = sorted(isr.system.modules, key=lambda m: m.id)
        for i in range(min(len(modules), population_size)):
            module = modules[i]
            intent = DeploymentIntent(
                deployment_id=f"dep.{module.id}",
                target_refs=(module.id,),
                rollout_strategy=RolloutStrategy.PROGRESSIVE,
                rollout_constraints=("at most one degraded target",),
                health_requirements=("target remains reachable",),
                rollback_required=True,
                rollback_target_ref=module.id,
                rollback_invariants=("target state preserved",),
                preservation_requirements=("no data loss",),
            )
            candidates.append(self.add_intent(isr, intent))
        return tuple(candidates)
