"""R2.10.3-E — the boundary mutation operator (gene-level mutation).

``BoundaryOperator`` mutates the boundary gene class alone:
add/remove/set-forbidden-dependencies. It never touches behavior, capability,
migration, temporal, reliability, or entity genes — the mutation-locality
contract that makes ``architectural_boundaries`` independently evolvable.

Removal of a PROTECTED boundary is rejected with ``ConstitutionalViolation`` —
the R2.8.6 protected-boundary semantics, elevated into the operator: the
boundary gene DECLARES the constraint, and this operator upholds the
declaration at the mutation boundary. (Wiring the R2.8.6 enforcement
machinery to read from the gene is a follow-up integration, deliberately not
part of this landing.)

A boundary's gene is (enclosed members, forbidden dependencies, protected
flag, crossing invariants) — a semantic constraint on relationships, never a
realization. No operator here can attach a package/container/process/network
concept, because the construct has no field for one.

Every mutation is attributed in the ledger as an R2.8.3 MEASUREMENT event.
The operator is deterministic: identical inputs produce identical candidates.
"""
from __future__ import annotations

import dataclasses
import json
from typing import Optional, Sequence

from constitutional_architecture.isr.model import (
    ArchitecturalBoundary,
    BoundaryValidationError,
    ISR,
)
from constitutional_architecture.validators import ConstitutionalViolation

from .ledger import EventType, EvolutionEvent, EvolutionLedger, stable_isr_hash
from .mutation_operators import ISRDelta, MutationCandidate


class BoundaryOperator:
    """Mutates only the boundary gene class (System.architectural_boundaries)."""

    operator_id = "boundary"

    def __init__(self, ledger: Optional[EvolutionLedger] = None) -> None:
        self._ledger = ledger

    # -- rebuild helpers ------------------------------------------------------

    @staticmethod
    def _replace_boundaries(
        isr: ISR, boundaries: Sequence[ArchitecturalBoundary]
    ) -> ISR:
        return isr.with_system(
            dataclasses.replace(
                isr.system, architectural_boundaries=tuple(boundaries)
            )
        )

    @staticmethod
    def _candidate(
        isr: ISR,
        after: ISR,
        operation: str,
        boundary: ArchitecturalBoundary,
    ) -> MutationCandidate:
        delta = ISRDelta(
            (
                json.dumps(
                    {
                        "operator": "boundary",
                        "operation": operation,
                        "boundary_id": boundary.boundary_id,
                        "member_refs": list(boundary.member_refs),
                        "protected": boundary.protected,
                    },
                    sort_keys=True,
                ),
            )
        )
        return MutationCandidate(
            candidate_id=f"{BoundaryOperator.operator_id}:"
            f"{stable_isr_hash(after)[:12]}",
            operator_id=BoundaryOperator.operator_id,
            candidate_isr=after,
            parent_isr=isr,
            mutation_delta=delta,
            hypothesis=f"boundary: {operation} '{boundary.boundary_id}'",
        )

    # -- attribution ------------------------------------------------------------

    def _attest(
        self,
        before: ISR,
        after: ISR,
        operation: str,
        boundary: ArchitecturalBoundary,
    ) -> None:
        if self._ledger is None:
            return
        event = EvolutionEvent(
            event_id="",
            evolution_id="r2.10.3-e",
            sequence=0,
            event_type=EventType.MEASUREMENT,
            subject_id=boundary.boundary_id,
            isr_hash=stable_isr_hash(after),
            payload={
                "operator_id": self.operator_id,
                "operation": operation,
                "boundary_id": boundary.boundary_id,
                "member_refs": list(boundary.member_refs),
                "protected": boundary.protected,
                "isr_hash_before": stable_isr_hash(before),
                "isr_hash_after": stable_isr_hash(after),
            },
        )
        self._ledger.append_event(event, evolution_id="r2.10.3-e")

    # -- operations -----------------------------------------------------------------

    def add_boundary(
        self, isr: ISR, boundary: ArchitecturalBoundary
    ) -> MutationCandidate:
        """Declare one architectural boundary — nothing else changes."""
        existing = {
            b.boundary_id for b in isr.system.architectural_boundaries
        }
        if boundary.boundary_id in existing:
            raise BoundaryValidationError(
                f"architectural boundary '{boundary.boundary_id}' already declared"
            )
        after = self._replace_boundaries(
            isr, isr.system.architectural_boundaries + (boundary,)
        )
        self._attest(isr, after, "add_boundary", boundary)
        return self._candidate(isr, after, "add_boundary", boundary)

    def remove_boundary(
        self, isr: ISR, *, boundary_id: str
    ) -> MutationCandidate:
        """Remove one boundary.

        A PROTECTED boundary cannot be removed: its removal would be the
        silent-removal constitutional violation R2.8.6 guards against —
        elevated into the ISR as a first-class declaration.
        """
        for boundary in isr.system.architectural_boundaries:
            if boundary.boundary_id == boundary_id:
                if boundary.protected:
                    raise ConstitutionalViolation(
                        f"removal of protected boundary '{boundary_id}' rejected"
                    )
                after = self._replace_boundaries(
                    isr,
                    tuple(
                        b
                        for b in isr.system.architectural_boundaries
                        if b.boundary_id != boundary_id
                    ),
                )
                self._attest(isr, after, "remove_boundary", boundary)
                return self._candidate(isr, after, "remove_boundary", boundary)
        raise BoundaryValidationError(
            f"architectural boundary '{boundary_id}' not found"
        )

    def set_forbidden_refs(
        self,
        isr: ISR,
        *,
        boundary_id: str,
        forbidden_dependency_refs: tuple[str, ...],
    ) -> MutationCandidate:
        """Respecify what members must NOT depend on; every other dimension is untouched."""
        for boundary in isr.system.architectural_boundaries:
            if boundary.boundary_id == boundary_id:
                edited = dataclasses.replace(
                    boundary, forbidden_dependency_refs=forbidden_dependency_refs
                )
                after = self._replace_boundaries(
                    isr,
                    tuple(
                        edited if b.boundary_id == boundary_id else b
                        for b in isr.system.architectural_boundaries
                    ),
                )
                self._attest(isr, after, "set_forbidden_refs", edited)
                return self._candidate(isr, after, "set_forbidden_refs", edited)
        raise BoundaryValidationError(
            f"architectural boundary '{boundary_id}' not found"
        )

    # -- deterministic generation ---------------------------------------------------

    def generate(
        self,
        isr: ISR,
        *,
        seed: Optional[int] = None,
        population_size: int = 1,
    ) -> tuple[MutationCandidate, ...]:
        """Seed-replayable candidate generation over the boundary gene class.

        Deterministic by construction: candidates enclose the first
        ``population_size`` sorted module pairs, forbidding cross-dependency
        on the enclosing module's sibling — no randomness, ``seed`` accepted
        for protocol compatibility and reproducibility attestation.
        """
        del seed
        candidates: list[MutationCandidate] = []
        modules = sorted(isr.system.modules, key=lambda m: m.id)
        for i in range(min(len(modules) - 1, population_size)):
            first, second = modules[i], modules[i + 1]
            boundary = ArchitecturalBoundary(
                boundary_id=f"bd.{first.id}",
                member_refs=(first.id,),
                forbidden_dependency_refs=(second.id,),
                protected=False,
                crossing_invariants=(
                    f"{first.id} must not cross to {second.id}",
                ),
            )
            candidates.append(self.add_boundary(isr, boundary))
        if not candidates:
            # Single-module ISRs: fall back to capability-enclosing boundaries.
            capabilities = sorted(
                isr.system.business_capabilities, key=lambda c: c.capability_id
            )
            for i in range(min(len(capabilities), population_size)):
                capability = capabilities[i]
                boundary = ArchitecturalBoundary(
                    boundary_id=f"bd.{capability.capability_id}",
                    member_refs=(capability.capability_id,),
                    forbidden_dependency_refs=(),
                    protected=False,
                    crossing_invariants=(
                        f"{capability.capability_id} must not cross without "
                        f"declared intent",
                    ),
                )
                candidates.append(self.add_boundary(isr, boundary))
        return tuple(candidates)