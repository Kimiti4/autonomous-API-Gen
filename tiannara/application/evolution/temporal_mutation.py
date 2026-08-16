"""R2.10.3-A — the temporal mutation operator (gene-level mutation).

``TemporalConstraintOperator`` mutates the temporal gene class alone:
add/edit/remove ``Module.temporal_constraints`` entries. It never touches
transition, state, or await-surface genes — the mutation-locality contract
that makes ``behavior_temporal_semantics`` independently evolvable.

Every mutation is attributed in the ledger as an R2.8.3 MEASUREMENT event
(operator_id + before/after hashes), so lineage is chain-anchored. The
operator is deterministic: identical inputs produce identical candidates
(the reproducibility gate).
"""
from __future__ import annotations

import dataclasses
import json
from typing import Optional, Sequence

from constitutional_architecture.isr.model import (
    ISR,
    TemporalConstraint,
    TemporalConstraintKind,
)

from .ledger import EventType, EvolutionEvent, EvolutionLedger, stable_isr_hash
from .mutation_operators import ISRDelta, MutationCandidate


class TemporalConstraintOperator:
    """Mutates only the temporal gene class (Module.temporal_constraints)."""

    operator_id = "temporal_constraint"

    def __init__(self, ledger: Optional[EvolutionLedger] = None) -> None:
        self._ledger = ledger

    # -- rebuild helpers ------------------------------------------------------

    @staticmethod
    def _replace_module_constraints(
        isr: ISR, module_id: str, constraints: Sequence[TemporalConstraint]
    ) -> ISR:
        modules = []
        for module in isr.system.modules:
            if module.id == module_id:
                module = dataclasses.replace(
                    module, temporal_constraints=tuple(constraints)
                )
            modules.append(module)
        return isr.with_system(dataclasses.replace(isr.system, modules=tuple(modules)))

    @staticmethod
    def _resolve_module(isr: ISR, transition_id: str) -> str:
        """Module containing a transition id (raises ValueError if unresolvable)."""
        for module in isr.system.modules:
            if any(
                t.id == transition_id for wf in module.workflows for t in wf.transitions
            ):
                return module.id
        raise ValueError(f"transition '{transition_id}' not found in any module")

    @staticmethod
    def _candidate(
        isr: ISR, after: ISR, operation: str, constraint: TemporalConstraint
    ) -> MutationCandidate:
        delta = ISRDelta(
            (
                json.dumps(
                    {
                        "operator": "temporal_constraint",
                        "operation": operation,
                        "constraint_id": constraint.constraint_id,
                        "kind": constraint.kind.value,
                        "target_ref": constraint.target_ref,
                        "duration_ms": constraint.duration_ms,
                        "reference_ref": constraint.reference_ref,
                    },
                    sort_keys=True,
                ),
            )
        )
        return MutationCandidate(
            candidate_id=f"{TemporalConstraintOperator.operator_id}:"
            f"{stable_isr_hash(after)[:12]}",
            operator_id=TemporalConstraintOperator.operator_id,
            candidate_isr=after,
            parent_isr=isr,
            mutation_delta=delta,
            hypothesis=f"temporal: {operation} {constraint.kind.value} on "
            f"{constraint.target_ref} ({constraint.duration_ms}ms)",
        )

    # -- attribute ------------------------------------------------------------------

    def _attest(
        self, before: ISR, after: ISR, operation: str, constraint: TemporalConstraint
    ) -> None:
        if self._ledger is None:
            return
        event = EvolutionEvent(
            event_id="",
            evolution_id="r2.10.3-a",
            sequence=0,
            event_type=EventType.MEASUREMENT,
            subject_id=constraint.constraint_id,
            isr_hash=stable_isr_hash(after),
            payload={
                "operator_id": self.operator_id,
                "operation": operation,
                "constraint_id": constraint.constraint_id,
                "kind": constraint.kind.value,
                "target_ref": constraint.target_ref,
                "duration_ms": constraint.duration_ms,
                "reference_ref": constraint.reference_ref,
                "isr_hash_before": stable_isr_hash(before),
                "isr_hash_after": stable_isr_hash(after),
            },
        )
        self._ledger.append_event(event, evolution_id="r2.10.3-a")

    # -- operations -----------------------------------------------------------------

    def add_deadline(
        self,
        isr: ISR,
        *,
        transition_id: str,
        duration_ms: int,
        constraint_id: Optional[str] = None,
        module_id: Optional[str] = None,
    ) -> MutationCandidate:
        """Add a TRANSITION_DEADLINE on one transition — nothing else changes."""
        module_id = module_id or self._resolve_module(isr, transition_id)
        constraint = TemporalConstraint(
            constraint_id=constraint_id or f"{transition_id}.deadline",
            kind=TemporalConstraintKind.TRANSITION_DEADLINE,
            target_ref=transition_id,
            duration_ms=duration_ms,
        )
        module = next(m for m in isr.system.modules if m.id == module_id)
        after = self._replace_module_constraints(
            isr, module_id, module.temporal_constraints + (constraint,)
        )
        self._attest(isr, after, "add_deadline", constraint)
        return self._candidate(isr, after, "add_deadline", constraint)

    def add_min_duration(
        self,
        isr: ISR,
        *,
        state_id: str,
        duration_ms: int,
        constraint_id: Optional[str] = None,
        module_id: Optional[str] = None,
    ) -> MutationCandidate:
        """Add a STATE_MIN_DURATION on one state."""
        module_id = module_id or self._module_for_state(isr, state_id)
        constraint = TemporalConstraint(
            constraint_id=constraint_id or f"{state_id}.min-duration",
            kind=TemporalConstraintKind.STATE_MIN_DURATION,
            target_ref=state_id,
            duration_ms=duration_ms,
        )
        module = next(m for m in isr.system.modules if m.id == module_id)
        after = self._replace_module_constraints(
            isr, module_id, module.temporal_constraints + (constraint,)
        )
        self._attest(isr, after, "add_min_duration", constraint)
        return self._candidate(isr, after, "add_min_duration", constraint)

    def add_event_ordering(
        self,
        isr: ISR,
        *,
        event_id: str,
        preceding_event_id: str,
        duration_ms: int,
        constraint_id: Optional[str] = None,
        module_id: Optional[str] = None,
    ) -> MutationCandidate:
        """Add an EVENT_ORDERING window between two module events."""
        module_id = module_id or self._module_for_event(isr, event_id)
        constraint = TemporalConstraint(
            constraint_id=constraint_id or f"{event_id}.follows-{preceding_event_id}",
            kind=TemporalConstraintKind.EVENT_ORDERING,
            target_ref=event_id,
            duration_ms=duration_ms,
            reference_ref=preceding_event_id,
        )
        module = next(m for m in isr.system.modules if m.id == module_id)
        after = self._replace_module_constraints(
            isr, module_id, module.temporal_constraints + (constraint,)
        )
        self._attest(isr, after, "add_event_ordering", constraint)
        return self._candidate(isr, after, "add_event_ordering", constraint)

    def edit_duration(
        self, isr: ISR, *, constraint_id: str, new_duration_ms: int
    ) -> MutationCandidate:
        """Rescale one constraint's duration; the constraint stays in place."""
        for module in isr.system.modules:
            for constraint in module.temporal_constraints:
                if constraint.constraint_id == constraint_id:
                    edited = dataclasses.replace(
                        constraint, duration_ms=new_duration_ms
                    )
                    constraints = tuple(
                        edited if c.constraint_id == constraint_id else c
                        for c in module.temporal_constraints
                    )
                    after = self._replace_module_constraints(
                        isr, module.id, constraints
                    )
                    self._attest(isr, after, "edit_duration", edited)
                    return self._candidate(isr, after, "edit_duration", edited)
        raise ValueError(f"temporal constraint '{constraint_id}' not found")

    def remove_constraint(
        self, isr: ISR, *, constraint_id: str
    ) -> MutationCandidate:
        """Remove a constraint — the remaining genes are untouched."""
        for module in isr.system.modules:
            for constraint in module.temporal_constraints:
                if constraint.constraint_id == constraint_id:
                    constraints = tuple(
                        c
                        for c in module.temporal_constraints
                        if c.constraint_id != constraint_id
                    )
                    after = self._replace_module_constraints(
                        isr, module.id, constraints
                    )
                    self._attest(isr, after, "remove_constraint", constraint)
                    return self._candidate(isr, after, "remove_constraint", constraint)
        raise ValueError(f"temporal constraint '{constraint_id}' not found")

    # -- deterministic generation ---------------------------------------------------

    def generate(
        self,
        isr: ISR,
        *,
        seed: Optional[int] = None,
        population_size: int = 1,
    ) -> tuple[MutationCandidate, ...]:
        """Seed-replayable candidate generation over the temporal gene class.

        Deterministic by construction: candidates are derived in sorted
        (module, target) order and carry no randomness — ``seed`` is accepted
        for protocol compatibility and reproducibility attestation.
        """
        del seed
        candidates: list[MutationCandidate] = []
        for module in sorted(isr.system.modules, key=lambda m: m.id):
            transitions = sorted(
                (t.id for wf in module.workflows for t in wf.transitions)
            )
            for transition_id in transitions[:population_size]:
                candidates.append(
                    self.add_deadline(
                        isr, transition_id=transition_id, duration_ms=250
                    )
                )
        return tuple(candidates)

    # -- resolvers ------------------------------------------------------------------

    @staticmethod
    def _module_for_state(isr: ISR, state_id: str) -> str:
        for module in isr.system.modules:
            if any(s.id == state_id for wf in module.workflows for s in wf.states):
                return module.id
        raise ValueError(f"state '{state_id}' not found in any module")

    @staticmethod
    def _module_for_event(isr: ISR, event_id: str) -> str:
        for module in isr.system.modules:
            if any(e.id == event_id for e in module.events):
                return module.id
        raise ValueError(f"event '{event_id}' not found in any module")