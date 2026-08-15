"""R2.9.2 -- autonomous constructive variation.

The variation engine is a *hypothesis generator*, never a judge. It proposes
ISR-level mutations (deltas with an ``op`` dispatch -- see
``apply_restoration``); every proposal is then scored by the same R2.6/R2.8
boundary (``CandidateGate`` + ``FitnessVector`` + Pareto) the repair is judged
by, and a candidate cannot improve its standing by touching the evaluation
surface (see ``AwaitingSurfaceIntactInvariant`` and the deceptive
``TestDeletionMutation`` control).

R2.9.2 policy:

* Mutation-primary: targeted operators propose exactly one deterministic
  candidate each (or decline). ``FSMRepairVariation`` composes them with a
  bounded, seed-replayable exploration operator.
* Crossover is deferred to R2.10: ``CrossoverOperator`` is the open port, and
  ``NullCrossover`` occupies it (identity semantics) so the R2.10 splice-in is
  a drop-in replacement without touching the coordinator.
* No scalar ``ConstructiveObjective``: the R2.6 ``FitnessVector`` is the only
  fitness contract; this module proposes, the boundary disposes.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional, Protocol, Sequence

from constitutional_architecture.isr.model import ISR

from tiannara.application.evolution.candidate_gate import GateContext
from tiannara.application.evolution.ledger import stable_isr_hash
from tiannara.application.evolution.mutation_operators import (
    ISRDelta,
    MutationCandidate,
    MutationOperator,
    NullMutation,
    TransitionRestorationOperator,
)
from tiannara.application.evolution.transition_restoration import (
    TransitionRestoration,
    apply_restoration,
)
from tiannara.domain.models.observation import FailureObservation


class ConstructiveVariationOperator(Protocol):
    """A population-level hypothesis generator.

    ``generate`` is deterministic under ``(defective_isr, observation, seed)``:
    replaying the same triple reproduces the same candidate set and order.
    """

    def generate(
        self,
        defective_isr: ISR,
        observation: FailureObservation,
        population_size: int,
        seed: int,
    ) -> Sequence[MutationCandidate]:
        ...


class CrossoverOperator(Protocol):
    """R2.10 port: recombine two ISRs. Deferred -- R2.9.2 ships ``NullCrossover``."""

    def crossover(
        self, parent_a: ISR, parent_b: ISR, seed: int
    ) -> Sequence[ISR]:
        ...


class NullCrossover:
    """R2.10 placeholder: recombination is identity (the parents, unchanged).

    Structural crossover (FSM graph-splicing) is deferred because splicing is
    destructive on the R2.9 substrate; keeping the port occupied by an honest
    identity implementation lets the coordinator wire generations without
    pretending recombination happened.
    """

    name = "null_crossover"

    def crossover(self, parent_a: ISR, parent_b: ISR, seed: int) -> Sequence[ISR]:
        return (parent_a, parent_b)


def _coroutine_name(observation: FailureObservation) -> Optional[str]:
    return TransitionRestoration().extract_coroutine_name(observation)


class GuardRelaxationOperator:
    """Targeted mutation: a transition that should fire is blocked by a
    ``guard_condition``; clear the guard.

    On the R2.9 FSM substrate the backend compiles trigger existence only, so a
    guarded resolution edge still awaits -- this operator is genuinely
    inapplicable there (declines). It exists as a replaceable targeted option
    for future substrates where guards gate codegen, and is unit-proven
    deterministically.
    """

    operator_id = "guard_relaxation"

    def propose(
        self, broken_isr: ISR, observation: FailureObservation
    ) -> Optional[MutationCandidate]:
        coroutine_name = _coroutine_name(observation)
        if coroutine_name is None:
            return None
        target = _find_transition(broken_isr, coroutine_name, guarded_only=True)
        if target is None:
            return None
        workflow_id, transition = target
        desc = {
            "workflow_id": workflow_id,
            "from_state_id": transition.from_state_id,
            "to_state_id": transition.to_state_id,
            "trigger": coroutine_name,
            "op": "relax_guard",
            "transition_id": transition.id,
        }
        return _candidate(
            self.operator_id, broken_isr, desc,
            hypothesis=(
                f"relax guard on transition '{transition.id}' blocking "
                f"resolution of '{coroutine_name}'"
            ),
        )


class ActionInjectionOperator:
    """Targeted mutation: the resolving transition fires but is missing a
    declared side-effect action; attach it.

    Like ``GuardRelaxationOperator`` this is a replaceable targeted option:
    on the R2.9 substrate actions do not affect codegen, so the CausalGate
    rejects the candidate (the artifact is unchanged) -- the boundary honestly
    records that the mutation was causally inert, which is exactly the
    discipline R2.9.2 requires of a hypothesis generator.
    """

    operator_id = "action_injection"

    def __init__(self, action: str = "notify-resolution"):
        self._action = action

    def propose(
        self, broken_isr: ISR, observation: FailureObservation
    ) -> Optional[MutationCandidate]:
        coroutine_name = _coroutine_name(observation)
        if coroutine_name is None:
            return None
        target = _find_transition(broken_isr, coroutine_name, guarded_only=False)
        if target is None:
            return None
        workflow_id, transition = target
        desc = {
            "workflow_id": workflow_id,
            "from_state_id": transition.from_state_id,
            "to_state_id": transition.to_state_id,
            "trigger": coroutine_name,
            "op": "inject_action",
            "transition_id": transition.id,
            "action": self._action,
        }
        return _candidate(
            self.operator_id, broken_isr, desc,
            hypothesis=(
                f"inject action '{self._action}' on transition "
                f"'{transition.id}' resolving '{coroutine_name}'"
            ),
        )


class RandomFSMExploration:
    """Bounded, seed-replayable exploratory variation.

    Proposes random *structurally valid* transitions between existing workflow
    states using a trigger pool that deliberately excludes the observed
    coroutine (so exploration never fabricates the exact repair -- that is the
    targeted operator's job). On the R2.9 substrate exploration edges do not
    change codegen, so the CausalGate rejects them as causally inert; the
    operator's contract is bounded, deterministic hypothesis generation, not
    acceptance.
    """

    operator_id = "random_fsm_exploration"

    def __init__(
        self,
        trigger_pool: tuple[str, ...] = ("poll", "retry", "timeout"),
        max_candidates: int = 4,
        rng_factory=random.Random,
    ):
        self._trigger_pool = trigger_pool
        self._max_candidates = max_candidates
        self._rng_factory = rng_factory

    def generate(
        self,
        defective_isr: ISR,
        observation: FailureObservation,
        population_size: int,
        seed: int,
    ) -> Sequence[MutationCandidate]:
        rng = self._rng_factory(seed)
        budget = min(self._max_candidates, max(0, population_size))
        candidates: list[MutationCandidate] = []
        for module in defective_isr.system.modules:
            for wf in module.workflows:
                if len(candidates) >= budget:
                    break
                state_ids = [s.id for s in wf.states]
                if len(state_ids) < 2:
                    continue
                edges: list[tuple[str, str, str]] = []
                for from_state_id in state_ids:
                    for to_state_id in state_ids:
                        if from_state_id == to_state_id:
                            continue
                        for trigger in self._trigger_pool:
                            edges.append((from_state_id, to_state_id, trigger))
                rng.shuffle(edges)
                for from_state_id, to_state_id, trigger in edges:
                    if len(candidates) >= budget:
                        break
                    desc = {
                        "workflow_id": wf.id,
                        "from_state_id": from_state_id,
                        "to_state_id": to_state_id,
                        "trigger": trigger,
                        "op": "explore",
                    }
                    candidates.append(_candidate(
                        self.operator_id, defective_isr, desc,
                        hypothesis=(
                            f"explore transition {from_state_id} -> "
                            f"{to_state_id} on '{trigger}'"
                        ),
                    ))
        return tuple(candidates)


class TestDeletionMutation:
    """Deceptive control: strip the awaiting surface the failing test checks.

    ISR-level analog of "delete the test that checks the transition": removing
    the ``awaits`` metadata makes the generated async surface stop firing the
    coroutine, so the target signature disappears without any real repair. The
    R2.8 boundary must reject this at the identity layer
    (``AwaitingSurfaceIntactInvariant``). Never part of a production ensemble;
    this is the R2.9.2 negative control proving the boundary is not
    test-deletion-gamed.
    """

    operator_id = "test_deletion"

    def propose(
        self, broken_isr: ISR, observation: FailureObservation
    ) -> Optional[MutationCandidate]:
        coroutine_name = _coroutine_name(observation)
        if coroutine_name is None:
            return None
        awaiting = _find_awaiting_state(broken_isr, coroutine_name)
        if awaiting is None:
            return None
        workflow_id, state = awaiting
        desc = {
            "workflow_id": workflow_id,
            "from_state_id": state.id,
            "to_state_id": state.id,
            "trigger": coroutine_name,
            "op": "strip_awaits",
            "state_id": state.id,
        }
        return _candidate(
            self.operator_id, broken_isr, desc,
            hypothesis=(
                f"strip awaiting surface of state '{state.id}' (deceptive: "
                f"the generated test no longer exercises '{coroutine_name}')"
            ),
        )


class FSMRepairVariation:
    """Default R2.9.2 constructive variation: targeted operators + exploration.

    ``generate`` is deterministic under ``(defective_isr, observation, seed)``:
    targeted operators are pure functions of the inputs, exploration is seeded
    from ``seed``, candidates are de-duplicated by ``candidate_id`` and ordered
    by it, and the population is bounded by ``population_size``.
    """

    def __init__(
        self,
        targeted_operators: Optional[Sequence[MutationOperator]] = None,
        exploration_operator: Optional[RandomFSMExploration] = None,
    ):
        self._targeted_operators = tuple(
            targeted_operators
            if targeted_operators is not None
            else (
                TransitionRestorationOperator(),
                NullMutation(),
                GuardRelaxationOperator(),
                ActionInjectionOperator(),
            )
        )
        self._exploration_operator = exploration_operator or RandomFSMExploration()

    def generate(
        self,
        defective_isr: ISR,
        observation: FailureObservation,
        population_size: int,
        seed: int,
    ) -> Sequence[MutationCandidate]:
        seen: dict[str, MutationCandidate] = {}
        for op in self._targeted_operators:
            proposed = op.propose(defective_isr, observation)
            if proposed is not None:
                seen.setdefault(proposed.candidate_id, proposed)
        for candidate in self._exploration_operator.generate(
            defective_isr, observation, population_size, seed
        ):
            seen.setdefault(candidate.candidate_id, candidate)
        ordered = sorted(seen.values(), key=lambda c: c.candidate_id)
        return tuple(ordered[:population_size])


@dataclass(frozen=True)
class AwaitingSurfaceIntactInvariant:
    """R2.8 identity layer for the FSM substrate: no candidate may drop,
    rename, or re-point an awaiting surface declared by its parent.

    A repair may add awaiting surfaces, but the set ``(workflow, state) ->
    coroutine`` must be preserved -- this is what refuses
    ``TestDeletionMutation`` ("delete the test that checks the transition")
    at the invariant gate.
    """

    invariant_id = "awaiting_surface_intact"

    @staticmethod
    def _surface(isr: ISR) -> dict[tuple[str, str], str]:
        out: dict[tuple[str, str], str] = {}
        for module in isr.system.modules:
            for wf in module.workflows:
                for state in wf.states:
                    coroutine = state.metadata.get("awaits")
                    if coroutine:
                        out[(wf.id, state.id)] = coroutine
        return out

    def holds(self, ctx: GateContext) -> bool:
        parent = self._surface(ctx.parent_isr)
        candidate = self._surface(ctx.candidate_isr)
        return all(candidate.get(k) == v for k, v in parent.items())


# -- shared helpers ----------------------------------------------------------

def _find_transition(
    isr: ISR, coroutine_name: str, guarded_only: bool
) -> Optional[tuple[str, object]]:
    """Locate the single transition whose trigger matches the coroutine."""
    matches: list[tuple[str, object]] = []
    for module in isr.system.modules:
        for wf in module.workflows:
            for t in wf.transitions:
                if t.trigger != coroutine_name:
                    continue
                if guarded_only and not t.guard_condition:
                    continue
                matches.append((wf.id, t))
    if len(matches) == 1:
        return matches[0]
    return None


def _find_awaiting_state(
    isr: ISR, coroutine_name: str
) -> Optional[tuple[str, object]]:
    awaiting: list[tuple[str, object]] = []
    for module in isr.system.modules:
        for wf in module.workflows:
            for state in wf.states:
                if state.metadata.get("awaits") == coroutine_name:
                    awaiting.append((wf.id, state))
    if len(awaiting) == 1:
        return awaiting[0]
    return None


def _candidate(
    operator_id: str,
    parent_isr: ISR,
    desc: dict,
    hypothesis: str,
) -> MutationCandidate:
    import json

    entry = json.dumps(desc, sort_keys=True)
    delta = ISRDelta((entry,))
    candidate_isr = apply_restoration(parent_isr, delta.entries)
    return MutationCandidate(
        candidate_id=f"{operator_id}:{stable_isr_hash(candidate_isr)[:12]}",
        operator_id=operator_id,
        candidate_isr=candidate_isr,
        parent_isr=parent_isr,
        mutation_delta=delta,
        hypothesis=hypothesis,
    )