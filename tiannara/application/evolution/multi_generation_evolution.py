"""R2.9.3 -- Multi-generation autonomous evolution.

Extends the R2.9.2 single-generation repair into evolution over time. The
governing invariant is unchanged and now spans generations:

    variation proposes; the evaluation boundary decides;
    selection chooses; the ledger records.

Constitutional constraints (structural, not conventions):

* **Evaluation is re-run fresh every generation.** Each generation recompiles
  and re-runs its own parent ISR; no evidence cache crosses generations. A
  gen-N candidate can never launder gen-(N-1) evidence because the CausalGate
  binds every verdict to the generation's own ISR/artifact/recompile hash.
* **Lineage is the thread.** The selected candidate's ISR is the sole
  authoritative parent of the next generation. Every candidate must declare
  ``parent_isr_hash == current generation's parent``; a mismatch is a lineage
  break and the candidate is rejected before evaluation.
* **EvolutionState is search-process state, kept outside the ISR.**
* **Diversity is observed, never used as a selection objective.**

R2.9.3 documented policy -- elite advancement on no-feasible generations:

A generation whose Pareto frontier is empty does not automatically terminate
the run. Instead the deterministic elite candidate -- best by lexicographic
FitnessVector objectives (safety-first canonical order, see
``EliteAdvancementStrategy``) with candidate_id tie-break, never a scalar --
becomes the next generation's parent (``elite_advanced=True``). This is what
makes evolution over time real: the search can traverse hypotheses that do
not yet satisfy every gate. The run terminates ``NO_FEASIBLE_CANDIDATES``
only when the elite is identical to the current parent (no progress
possible). The elite policy is itself an injectable ``SelectionStrategy``
(replaceable without touching the coordinator).
"""
from __future__ import annotations

import tempfile
from typing import Optional, Sequence

from constitutional_architecture.isr.model import ISR

from tiannara.application.evolution.candidate_gate import CandidateGate
from tiannara.application.evolution.candidate_sandbox import CompiledCandidate
from tiannara.application.evolution.competitive_evolution import (
    EliteAdvancementStrategy,
    SelectionStrategy,
    pareto_frontier,
    score_candidate,
)
from tiannara.application.evolution.diversity import DiversityObserver
from tiannara.application.evolution.evolution_state import (
    DiversityMetrics,
    EvolutionState,
    GenerationState,
    PopulationSnapshot,
    TerminationReason,
    derive_evolution_id,
    derive_generation_id,
)
from tiannara.application.evolution.ledger import (
    EventType,
    EvolutionEvent,
    EvolutionLedger,
    stable_isr_hash,
)
from tiannara.application.evolution.variation import ConstructiveVariationOperator
from tiannara.domain.models.evidence import TestRunResult
from tiannara.domain.models.observation import FailureObservation


class MultiGenerationEvolutionCoordinator:
    """Runs a multi-generation search over the R2.8 evaluation boundary."""

    def __init__(
        self,
        sandbox: "RealBackendSandbox",
        gate: CandidateGate,
        variation: ConstructiveVariationOperator,
        selection: SelectionStrategy,
        ledger: Optional[EvolutionLedger] = None,
        diversity_observer: Optional[DiversityObserver] = None,
        stagnation_window: int = 3,
        elite_strategy: Optional[SelectionStrategy] = None,
    ):
        self._sandbox = sandbox
        self._gate = gate
        self._variation = variation
        self._selection = selection
        self._ledger = ledger
        self._diversity = diversity_observer or DiversityObserver()
        self._stagnation_window = stagnation_window
        #: The no-feasible policy is itself a replaceable selection stage.
        self._elite_strategy = elite_strategy or EliteAdvancementStrategy()

    # -- public API ----------------------------------------------------------

    def run(
        self,
        defective_isr: ISR,
        observation: FailureObservation,
        broken_artifact: CompiledCandidate,
        broken_run: TestRunResult,
        baseline_artifact: CompiledCandidate,
        baseline_run: TestRunResult,
        max_generations: int,
        population_size: int,
        seed: int,
        protected_invariants: tuple = (),
    ) -> EvolutionState:
        from tiannara.application.evolution.compiler_sandbox import hash_artifact

        initial_isr_hash = stable_isr_hash(defective_isr)
        evolution_id = derive_evolution_id(
            initial_isr_hash, observation.evidence_hash, seed
        )
        self._evolution_id = evolution_id
        self._emit(
            EventType.OBSERVATION,
            payload={"evolution_id": evolution_id, "seed": seed},
            observation_hash=observation.evidence_hash,
        )

        current_isr = defective_isr
        current_isr_hash = initial_isr_hash
        # Gen-0 parent evidence comes from the caller (fresh, bound to the
        # defective ISR). Every later generation rebuilds + re-runs its parent.
        parent_artifact, parent_run = broken_artifact, broken_run
        parent_gen_id: Optional[str] = None
        generations: list[GenerationState] = []
        recent_selected_hashes: list[Optional[str]] = []

        for index in range(max_generations):
            gen_id = derive_generation_id(evolution_id, index, current_isr_hash)

            # 1. Variation -- deterministic under (ISR, observation, seed+index).
            raw_population = list(self._variation.generate(
                current_isr, observation, population_size, seed + index
            ))
            population = self._dedup(raw_population)
            if not population:
                self._complete_generation(
                    gen_id, generations, index, parent_gen_id, current_isr_hash,
                    population=(), scored=(), diversity=None,
                    selected_id=None, selected_hash=None, elite_advanced=False,
                    termination=TerminationReason.POPULATION_EXHAUSTION,
                )
                return self._state(
                    evolution_id, initial_isr_hash, generations,
                    TerminationReason.POPULATION_EXHAUSTION, current_isr_hash,
                )
            self._emit(
                EventType.CANDIDATE_GENERATED,
                payload={
                    "generation_id": gen_id,
                    "raw_count": len(raw_population),
                    "unique_count": len(population),
                },
                isr_hash=current_isr_hash,
            )

            # 2. Evaluate fresh through the R2.8 boundary (no evidence cache).
            #    Lineage: candidate must descend from the current parent.
            scored = []
            for candidate in population:
                if stable_isr_hash(candidate.parent_isr) != current_isr_hash:
                    self._emit(
                        EventType.CANDIDATE_REJECTED,
                        payload={
                            "generation_id": gen_id,
                            "reason": "lineage_break",
                            "candidate": candidate.candidate_id,
                        },
                        subject_id=candidate.candidate_id,
                    )
                    continue
                result = score_candidate(
                    self._sandbox, self._gate, candidate, baseline_artifact,
                    baseline_run, observation, current_isr, parent_artifact,
                    parent_run, hash_artifact(parent_artifact.source_root),
                    protected_invariants,
                )
                scored.append(result)
                self._emit(
                    EventType.CANDIDATE_EVALUATED,
                    payload={
                        "generation_id": gen_id,
                        "candidate": candidate.candidate_id,
                        "accept": result.verdict.accept,
                    },
                    subject_id=candidate.candidate_id,
                    candidate_hash=stable_isr_hash(candidate.candidate_isr),
                )
                self._emit(
                    EventType.GATE_EVALUATED,
                    payload={
                        "generation_id": gen_id,
                        "candidate": candidate.candidate_id,
                        "gates": {r.gate_id: r.passed for r in result.verdict.gate_results},
                    },
                    subject_id=candidate.candidate_id,
                )
                event_type = (
                    EventType.CANDIDATE_ACCEPTED if result.verdict.accept
                    else EventType.CANDIDATE_REJECTED
                )
                self._emit(
                    event_type,
                    payload={"generation_id": gen_id, "candidate": candidate.candidate_id},
                    subject_id=candidate.candidate_id,
                )

            # 3. Observe diversity (record only; never selects).
            diversity = self._diversity.observe(raw_population, scored)

            # All candidates forged: the run cannot continue under an
            # authoritative parent -- lineage integrity violation.
            if population and not scored:
                return self._finish(
                    evolution_id, initial_isr_hash, generations,
                    gen_id, index, parent_gen_id, current_isr_hash,
                    population, scored, diversity, None, None, False,
                    TerminationReason.LINEAGE_BREAK, current_isr_hash,
                )

            # 4. Pareto selection -- multi-objective, deterministic tie-break.
            feasible = [s for s in scored if s.verdict.accept]
            frontier = pareto_frontier(feasible)
            selected = self._selection.select(frontier)
            selected_id = selected.candidate.candidate_id if selected else None
            selected_hash = (
                stable_isr_hash(selected.candidate.candidate_isr) if selected else None
            )
            next_parent_isr = selected.candidate.candidate_isr if selected else None
            if selected is not None:
                self._emit(
                    EventType.CANDIDATE_SELECTED,
                    payload={
                        "generation_id": gen_id,
                        "selected": selected_id,
                        "frontier_size": len(frontier),
                    },
                    subject_id=selected_id,
                    candidate_hash=selected_hash,
                )

            # 5. Termination checks.
            if selected is not None and self._resolves_observation(selected, observation):
                return self._finish(
                    evolution_id, initial_isr_hash, generations,
                    gen_id, index, parent_gen_id, current_isr_hash,
                    population, scored, diversity, selected_id, selected_hash,
                    False, TerminationReason.SUCCESS, selected_hash,
                )

            # 6. No-feasible policy: advance the deterministic elite when it
            #    improves on the parent; otherwise terminate.
            elite = None
            elite_advanced = False
            if selected is None:
                elite = self._elite_strategy.select(list(scored))
                elite_advanced = elite is not None and not _same_isr(
                    elite.candidate.candidate_isr, current_isr
                )
                if not elite_advanced:
                    return self._finish(
                        evolution_id, initial_isr_hash, generations,
                        gen_id, index, parent_gen_id, current_isr_hash,
                        population, scored, diversity, None, None, True,
                        TerminationReason.NO_FEASIBLE_CANDIDATES, current_isr_hash,
                    )
                selected_id = elite.candidate.candidate_id
                selected_hash = stable_isr_hash(elite.candidate.candidate_isr)
                next_parent_isr = elite.candidate.candidate_isr
                self._emit(
                    EventType.CANDIDATE_SELECTED,
                    payload={
                        "generation_id": gen_id,
                        "selected": selected_id,
                        "frontier_size": 0,
                        "note": "elite advancement (no feasible candidate)",
                    },
                    subject_id=selected_id,
                    candidate_hash=selected_hash,
                )
                recent_selected_hashes.append(selected_hash)
            else:
                recent_selected_hashes.append(selected_hash)

            # 7. Stagnation: the same ISR selected for the window.
            if self._is_stagnant(recent_selected_hashes):
                return self._finish(
                    evolution_id, initial_isr_hash, generations,
                    gen_id, index, parent_gen_id, current_isr_hash,
                    population, scored, diversity, selected_id, selected_hash,
                    elite_advanced, TerminationReason.STAGNATION, current_isr_hash,
                )

            # 8. Thread the selected ISR as the next generation's parent and
            #    compile/run it FRESH (the next generation's baseline evidence).
            parent_isr = next_parent_isr
            generations.append(self._gen_state(
                gen_id, index, parent_gen_id, current_isr_hash, population,
                scored, feasible, frontier, selected_id, selected_hash,
                elite_advanced, diversity,
            ))
            self._emit(
                EventType.GENERATION_COMPLETED,
                payload={
                    "generation_id": gen_id,
                    "diversity_entropy": diversity.genotype_entropy,
                    "duplicate_rate": diversity.duplicate_rate,
                    "feasible_count": len(feasible),
                },
            )
            current_isr = parent_isr
            current_isr_hash = selected_hash
            parent_gen_id = gen_id
            parent_artifact = self._sandbox.build(
                current_isr, workspace=tempfile.mkdtemp(prefix="r293-gen-")
            )
            parent_run = self._sandbox.run_tests(parent_artifact)

        return EvolutionState(
            evolution_id=evolution_id,
            initial_isr_hash=initial_isr_hash,
            generations=tuple(generations),
            termination_reason=TerminationReason.GENERATION_LIMIT,
            final_isr_hash=current_isr_hash,
        )

    # -- internals -----------------------------------------------------------

    def _finish(
        self, evolution_id, initial_isr_hash, generations,
        gen_id, index, parent_gen_id, parent_isr_hash,
        population, scored, diversity, selected_id, selected_hash,
        elite_advanced, reason, final_isr_hash,
    ) -> EvolutionState:
        generations.append(self._gen_state(
            gen_id, index, parent_gen_id, parent_isr_hash, population,
            scored, [s for s in scored if s.verdict.accept],
            pareto_frontier([s for s in scored if s.verdict.accept]),
            selected_id, selected_hash, elite_advanced, diversity,
        ))
        self._emit(
            EventType.GENERATION_COMPLETED,
            payload={
                "generation_id": gen_id,
                "termination": reason.value,
                "diversity_entropy": diversity.genotype_entropy if diversity else None,
                "duplicate_rate": diversity.duplicate_rate if diversity else None,
                "feasible_count": sum(1 for s in scored if s.verdict.accept),
            },
        )
        return EvolutionState(
            evolution_id=evolution_id,
            initial_isr_hash=initial_isr_hash,
            generations=tuple(generations),
            termination_reason=reason,
            final_isr_hash=final_isr_hash,
        )

    def _gen_state(
        self, gen_id, index, parent_gen_id, parent_isr_hash,
        population, scored, feasible, frontier, selected_id, selected_hash,
        elite_advanced, diversity,
    ) -> GenerationState:
        return GenerationState(
            generation_id=gen_id,
            generation_index=index,
            parent_generation_id=parent_gen_id,
            parent_isr_hash=parent_isr_hash,
            population_snapshot=PopulationSnapshot(
                tuple(c.candidate_id for c in population)
            ),
            evaluated_count=len(scored),
            feasible_count=len(feasible),
            frontier_size=len(frontier),
            selected_candidate_id=selected_id,
            selected_isr_hash=selected_hash,
            elite_advanced=elite_advanced,
            diversity=diversity,
        )

    def _complete_generation(self, gen_id, generations, index, parent_gen_id,
                             parent_isr_hash, population, scored, diversity,
                             selected_id, selected_hash, elite_advanced,
                             termination) -> None:
        """Record a final generation that produced no candidates at all."""
        generations.append(GenerationState(
            generation_id=gen_id,
            generation_index=index,
            parent_generation_id=parent_gen_id,
            parent_isr_hash=parent_isr_hash,
            population_snapshot=PopulationSnapshot(()),
            evaluated_count=0,
            feasible_count=0,
            frontier_size=0,
            selected_candidate_id=None,
            selected_isr_hash=None,
            elite_advanced=False,
            diversity=diversity or DiversityMetrics(
                0, 0, 0, {}, 0.0, 0.0, 0.0
            ),
        ))
        self._emit(
            EventType.GENERATION_COMPLETED,
            payload={
                "generation_id": gen_id,
                "termination": termination.value,
                "feasible_count": 0,
            },
        )

    @staticmethod
    def _resolves_observation(scored, observation: FailureObservation) -> bool:
        """Derived per design: the observation is resolved when the selected
        candidate passed the target_failure gate (the boundary's own verdict --
        never a separate judge)."""
        return any(
            r.gate_id == "target_failure" and r.passed
            for r in scored.verdict.gate_results
        )

    @staticmethod
    def _dedup(candidates: Sequence) -> list:
        seen: set[str] = set()
        unique = []
        for c in candidates:
            if c.candidate_id not in seen:
                seen.add(c.candidate_id)
                unique.append(c)
        return unique

    def _is_stagnant(self, recent: list[Optional[str]]) -> bool:
        if len(recent) < self._stagnation_window:
            return False
        window = recent[-self._stagnation_window:]
        return len(set(window)) == 1 and window[0] is not None

    @staticmethod
    def _state(evolution_id, initial_isr_hash, generations, reason, final_isr_hash):
        return EvolutionState(
            evolution_id=evolution_id,
            initial_isr_hash=initial_isr_hash,
            generations=tuple(generations),
            termination_reason=reason,
            final_isr_hash=final_isr_hash,
        )

    def _emit(self, event_type: EventType, *, payload: dict,
              subject_id: str = "", candidate_hash: str = "",
              observation_hash: str = "", isr_hash: str = "") -> None:
        if self._ledger is None:
            return
        event = EvolutionEvent(
            event_id="",
            evolution_id=self._evolution_id or "",
            sequence=0,
            event_type=event_type,
            parent_event_id="",
            subject_id=subject_id,
            payload=payload,
            observation_hash=observation_hash,
            candidate_hash=candidate_hash,
            isr_hash=isr_hash,
        )
        self._ledger.append_event(event, evolution_id=self._evolution_id or "")


def _same_isr(a: ISR, b: ISR) -> bool:
    return stable_isr_hash(a) == stable_isr_hash(b)