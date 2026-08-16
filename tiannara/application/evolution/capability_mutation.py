"""R2.10.3-B — the capability mutation operator (gene-level mutation).

``CapabilityOperator`` mutates the capability gene class alone:
add/remove/set-intent/edit-reference-membership. It never touches behavior,
interface, constraint, or temporal genes — the mutation-locality contract
that makes ``business_capabilities`` independently evolvable.

A capability's gene is (intent, refs-by-id): mutating a referenced
behavior's CONTENT does not touch the capability gene (references are ids,
not hashes); changing the capability's intent or membership does. That is
the capability-definition-mutation != behavior-mutation separation made
structural.

Every mutation is attributed in the ledger as an R2.8.3 MEASUREMENT event.
The operator is deterministic: identical inputs produce identical candidates.
"""
from __future__ import annotations

import dataclasses
import json
from typing import Optional, Sequence

from constitutional_architecture.isr.model import (
    BusinessCapability,
    CapabilityValidationError,
    ISR,
)

from .ledger import EventType, EvolutionEvent, EvolutionLedger, stable_isr_hash
from .mutation_operators import ISRDelta, MutationCandidate

REF_KINDS = ("behavior_refs", "interface_refs", "constraint_refs", "requirement_refs")


class CapabilityOperator:
    """Mutates only the capability gene class (System.business_capabilities)."""

    operator_id = "capability"

    def __init__(self, ledger: Optional[EvolutionLedger] = None) -> None:
        self._ledger = ledger

    # -- rebuild helpers ------------------------------------------------------

    @staticmethod
    def _replace_capabilities(
        isr: ISR, capabilities: Sequence[BusinessCapability]
    ) -> ISR:
        return isr.with_system(
            dataclasses.replace(
                isr.system, business_capabilities=tuple(capabilities)
            )
        )

    @staticmethod
    def _candidate(
        isr: ISR,
        after: ISR,
        operation: str,
        capability: BusinessCapability,
    ) -> MutationCandidate:
        delta = ISRDelta(
            (
                json.dumps(
                    {
                        "operator": "capability",
                        "operation": operation,
                        "capability_id": capability.capability_id,
                        "intent": capability.intent,
                        "behavior_refs": list(capability.behavior_refs),
                        "interface_refs": list(capability.interface_refs),
                        "constraint_refs": list(capability.constraint_refs),
                    },
                    sort_keys=True,
                ),
            )
        )
        return MutationCandidate(
            candidate_id=f"{CapabilityOperator.operator_id}:"
            f"{stable_isr_hash(after)[:12]}",
            operator_id=CapabilityOperator.operator_id,
            candidate_isr=after,
            parent_isr=isr,
            mutation_delta=delta,
            hypothesis=f"capability: {operation} '{capability.capability_id}'",
        )

    # -- attribution ------------------------------------------------------------

    def _attest(
        self,
        before: ISR,
        after: ISR,
        operation: str,
        capability: BusinessCapability,
    ) -> None:
        if self._ledger is None:
            return
        event = EvolutionEvent(
            event_id="",
            evolution_id="r2.10.3-b",
            sequence=0,
            event_type=EventType.MEASUREMENT,
            subject_id=capability.capability_id,
            isr_hash=stable_isr_hash(after),
            payload={
                "operator_id": self.operator_id,
                "operation": operation,
                "capability_id": capability.capability_id,
                "intent": capability.intent,
                "behavior_refs": list(capability.behavior_refs),
                "interface_refs": list(capability.interface_refs),
                "constraint_refs": list(capability.constraint_refs),
                "isr_hash_before": stable_isr_hash(before),
                "isr_hash_after": stable_isr_hash(after),
            },
        )
        self._ledger.append_event(event, evolution_id="r2.10.3-b")

    # -- operations -----------------------------------------------------------------

    def add_capability(self, isr: ISR, capability: BusinessCapability) -> MutationCandidate:
        """Declare a capability — nothing else changes."""
        existing = {c.capability_id for c in isr.system.business_capabilities}
        if capability.capability_id in existing:
            raise CapabilityValidationError(
                f"capability '{capability.capability_id}' already declared"
            )
        after = self._replace_capabilities(
            isr, isr.system.business_capabilities + (capability,)
        )
        self._attest(isr, after, "add_capability", capability)
        return self._candidate(isr, after, "add_capability", capability)

    def remove_capability(self, isr: ISR, *, capability_id: str) -> MutationCandidate:
        """Remove a capability — the referenced genes are untouched."""
        for capability in isr.system.business_capabilities:
            if capability.capability_id == capability_id:
                after = self._replace_capabilities(
                    isr,
                    tuple(
                        c
                        for c in isr.system.business_capabilities
                        if c.capability_id != capability_id
                    ),
                )
                self._attest(isr, after, "remove_capability", capability)
                return self._candidate(isr, after, "remove_capability", capability)
        raise CapabilityValidationError(f"capability '{capability_id}' not found")

    def set_capability_intent(
        self, isr: ISR, *, capability_id: str, intent: str
    ) -> MutationCandidate:
        """Respecify WHAT the capability means; its references are untouched."""
        for capability in isr.system.business_capabilities:
            if capability.capability_id == capability_id:
                edited = dataclasses.replace(capability, intent=intent)
                after = self._replace_capabilities(
                    isr,
                    tuple(
                        edited if c.capability_id == capability_id else c
                        for c in isr.system.business_capabilities
                    ),
                )
                self._attest(isr, after, "set_capability_intent", edited)
                return self._candidate(isr, after, "set_capability_intent", edited)
        raise CapabilityValidationError(f"capability '{capability_id}' not found")

    def add_capability_ref(
        self, isr: ISR, *, capability_id: str, ref_kind: str, ref_id: str
    ) -> MutationCandidate:
        """Change membership: add one reference of a kind (identity only)."""
        if ref_kind not in REF_KINDS:
            raise CapabilityValidationError(f"unknown ref_kind '{ref_kind}'")
        for capability in isr.system.business_capabilities:
            if capability.capability_id == capability_id:
                current = getattr(capability, ref_kind)
                if ref_id in current:
                    raise CapabilityValidationError(
                        f"reference '{ref_id}' already present in {ref_kind}"
                    )
                edited = dataclasses.replace(
                    capability, **{ref_kind: current + (ref_id,)}
                )
                after = self._replace_capabilities(
                    isr,
                    tuple(
                        edited if c.capability_id == capability_id else c
                        for c in isr.system.business_capabilities
                    ),
                )
                self._attest(isr, after, "add_capability_ref", edited)
                return self._candidate(isr, after, "add_capability_ref", edited)
        raise CapabilityValidationError(f"capability '{capability_id}' not found")

    # -- deterministic generation ---------------------------------------------------

    def generate(
        self,
        isr: ISR,
        *,
        seed: Optional[int] = None,
        population_size: int = 1,
    ) -> tuple[MutationCandidate, ...]:
        """Seed-replayable candidate generation over the capability gene class.

        Deterministic by construction: candidates are derived in sorted
        workflow order and carry no randomness — ``seed`` is accepted for
        protocol compatibility and reproducibility attestation.
        """
        del seed
        candidates: list[MutationCandidate] = []
        workflows = sorted(
            (wf for m in isr.system.modules for wf in m.workflows),
            key=lambda wf: wf.id,
        )
        for workflow in workflows[:population_size]:
            candidates.append(
                self.add_capability(
                    isr,
                    BusinessCapability(
                        capability_id=f"cap.{workflow.id}",
                        intent=f"provide {workflow.name}",
                        behavior_refs=(workflow.id,),
                    ),
                )
            )
        return tuple(candidates)