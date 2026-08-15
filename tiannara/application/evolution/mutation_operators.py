"""R2.6 -- mutation operators and candidates.

The Evolution Engine does not mutate generated artifacts; it mutates the ISR and
lets the (pure) compiler re-ground. A ``MutationCandidate`` is the unit the R2.5
``CandidateGate`` evaluates: an ISR delta together with its provenance (the
parent/broken ISR it was derived from) and a human-readable hypothesis.

Operators are plugins -- a tuple of them is the ensemble the
``CompetitiveEvolutionCoordinator`` searches. R2.6 ships two:

* ``TransitionRestorationOperator`` -- the R2.4.0b repair, wrapped as an
  ISRDelta candidate.
* ``NullMutation`` -- "choose restraint." A legitimate candidate, not a control:
  it represents the decision *not* to mutate. On the async-resolution defect it
  is rejected by ``TargetFailureGate`` (the failure persists); on a defect where
  every mutation is harmful, restraint is the correct selection. An engine that
  cannot refrain is not trustworthy.
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Optional, Protocol

from constitutional_architecture.isr.model import ISR

from tiannara.application.evolution.ledger import stable_isr_hash
from tiannara.application.evolution.transition_restoration import (
    RepairedCandidate,
    TransitionRestoration,
)
from tiannara.domain.models.observation import FailureObservation


@dataclass(frozen=True)
class ISRDelta:
    """Minimal, serializable ISR mutation.

    ``entries`` are R2.3 JSON descriptors (e.g.
    ``{"workflow_id","from_state_id","to_state_id","trigger"}``). An empty delta
    is the identity mutation produced by ``NullMutation`` -- structurally valid,
    changes nothing.
    """

    entries: tuple[str, ...] = ()

    @property
    def size(self) -> int:
        return len(self.entries)


EMPTY_DELTA = ISRDelta(())


@dataclass(frozen=True)
class MutationCandidate:
    """One ISR mutation proposed by an operator.

    ``candidate_id`` embeds the candidate's ISR hash so an operator proposing
    an already-seen ISR is de-duplicated by the coordinator before evaluation.
    """

    candidate_id: str
    operator_id: str
    candidate_isr: ISR
    parent_isr: ISR
    mutation_delta: ISRDelta
    hypothesis: str


class MutationOperator(Protocol):
    """Plugin interface for candidate generation."""

    operator_id: str

    def propose(
        self, broken_isr: ISR, observation: FailureObservation
    ) -> Optional[MutationCandidate]:
        ...


class TransitionRestorationOperator:
    """R2.4.0b repair, projected onto the R2.6 candidate contract."""

    operator_id = "transition_restoration"

    def __init__(self, restoration: Optional[TransitionRestoration] = None):
        self._restoration = restoration or TransitionRestoration()

    def propose(
        self, broken_isr: ISR, observation: FailureObservation
    ) -> Optional[MutationCandidate]:
        coro = self._restoration.extract_coroutine_name(observation)
        if coro is None:
            return None
        repaired: Optional[RepairedCandidate] = self._restoration.try_repair(
            broken_isr, coro
        )
        if repaired is None:
            return None
        delta = ISRDelta(tuple(repaired.repaired_diff))
        return MutationCandidate(
            candidate_id=f"{self.operator_id}:{stable_isr_hash(repaired.repaired_isr)[:12]}",
            operator_id=self.operator_id,
            candidate_isr=repaired.repaired_isr,
            parent_isr=broken_isr,
            mutation_delta=delta,
            hypothesis=repaired.hypothesis,
        )


class NullMutation:
    """The identity candidate: mutate nothing.

    Represents "choose restraint." Its delta is empty; the gate's CausalGate
    accepts the identity (closure + fresh-recompile hold), while
    TargetFailureGate rejects it when the target failure persists.
    """

    operator_id = "null_mutation"

    def propose(
        self, broken_isr: ISR, observation: FailureObservation
    ) -> MutationCandidate:
        return MutationCandidate(
            candidate_id=f"{self.operator_id}:{stable_isr_hash(broken_isr)[:12]}",
            operator_id=self.operator_id,
            candidate_isr=broken_isr,
            parent_isr=broken_isr,
            mutation_delta=EMPTY_DELTA,
            hypothesis="no mutation; choose restraint",
        )
