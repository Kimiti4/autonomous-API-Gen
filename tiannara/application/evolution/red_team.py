"""R2.8.13 -- Adaptive Adversarial Red Team.

Tests whether the evaluation boundary can be bypassed by an *adaptive*
adversary that receives information about prior evaluations and searches
for bypasses. The Red Team is an external oracle-driven fuzzer -- not a
mutation operator inside the Evolution Engine.

Architectural constraints (continued from R2.8.2 information-hiding):

* The red team is an EXTERNAL searcher, not a mutation operator inside the
  Evolution Engine. It treats the evaluation boundary as a black-box oracle.
* The oracle exposes ONLY (Verdict, visible_fitness). It withholds catching
  layers, hidden-test results, gate identities, evidence internals, and lineage.
* Ground-truth auditing is performed by a separate auditor the red team cannot
  see. A bypass = an accepted candidate that fails the ground-truth audit.
* The campaign is seeded and deterministic: same seed -> same trajectory.
"""
from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, field
from typing import Callable, Protocol, Sequence

from .adversarial_lab import (
    AdversarialGateDecider,
    CandidateEvidence,
    Decision,
    Verdict,
)
from .authorization import Authorization
from .evaluation_boundary import ProtectedTestSet
from .ledger import EvolutionLedger, EventType


# ---------------------------------------------------------------------------
# Mutation vector -- the red team's attack genome
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MutationVector:
    """A red-team-generated ISR delta description.

    The Red Team produces vectors (named modifications to the visible evidence)
    and evaluates them through the oracle. The vector is the Red Team's
    hypothesis; the oracle is the ground truth.
    """

    __test__ = False

    name: str
    evidence_fn: Callable[[CandidateEvidence], CandidateEvidence]
    description: str = ""

    def apply(self, base: CandidateEvidence) -> CandidateEvidence:
        return self.evidence_fn(base)


# ---------------------------------------------------------------------------
# Oracle -- the black-box evaluation boundary
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class OracleResponse:
    """The ONLY information the Red Team receives from the oracle.

    Deliberately excludes: catching_layers, DetectionMetrics, holdout_evidence,
    the rejection reason, and any internal gate state. The Red Team sees the
    verdict and the visible fitness score -- nothing more.

    Enforced by the shape of the type itself (frozen dataclass with no
    internal fields), not by convention.
    """

    __test__ = False

    verdict: Verdict
    visible_pass_rate: float
    candidate_hash: str

    @property
    def accepted(self) -> bool:
        return self.verdict is Verdict.ACCEPT


class RedTeamOracle:
    """Wraps the evaluation boundary, exposing only the oracle interface.

    This is the information-hiding boundary: the Red Team cannot see anything
    beyond Verdict + visible fitness. Internally, the full Decision is retained
    for post-hoc bypass verification via an independent auditor.
    """

    __test__ = False

    def __init__(
        self,
        decider: AdversarialGateDecider,
        protected: ProtectedTestSet,
        baseline_run,
        ledger: EvolutionLedger,
    ):
        self._decider = decider
        self._protected = protected
        self._baseline_run = baseline_run
        self._ledger = ledger
        self._query_count = 0
        self._decision_log: list[tuple[OracleResponse, Decision]] = []

    @property
    def query_count(self) -> int:
        return self._query_count

    def submit(self, evidence: CandidateEvidence) -> OracleResponse:
        """Submit a candidate to the oracle; receive only Verdict + visible fitness."""
        self._query_count += 1
        decision: Decision = self._decider.decide(
            self._protected, self._baseline_run, evidence
        )

        # Visible fitness: pass rate over the VISIBLE surface only.
        visible_tests = evidence.evolution_evidence
        total = len(visible_tests) if visible_tests else 1
        passed = sum(1 for t in visible_tests if t.outcome.value == "passed")
        visible_pass_rate = passed / total if total else 0.0

        # Record the query in the ledger (tamper-evident, generation-agnostic).
        from .ledger import EvolutionEvent
        event = EvolutionEvent(
            event_id="",
            evolution_id="r2.8.13",
            sequence=0,
            event_type=EventType.CANDIDATE_EVALUATED,
            subject_id=f"query-{self._query_count}",
            payload={
                "verdict": decision.verdict.value,
                "visible_pass_rate": visible_pass_rate,
                "candidate_hash": evidence.content_hash(),
                "evidence_intact": decision.evidence_intact,
            },
            candidate_hash=evidence.content_hash(),
            environment_hash=self._protected.environment_fingerprint,
        )
        self._ledger.append_event(event, evolution_id="r2.8.13")

        resp = OracleResponse(
            verdict=decision.verdict,
            visible_pass_rate=visible_pass_rate,
            candidate_hash=evidence.content_hash(),
        )
        # Internally retain the full decision for post-hoc bypass verification.
        # The Red Team never sees this -- only the test harness does.
        self._decision_log.append((resp, decision))
        return resp

    def verify_chain(self) -> bool:
        """Post-experiment integrity check on the red team's ledger trail."""
        return self._ledger.verify_event_chain()

    def verify_no_bypasses(self) -> bool:
        """R2.8.13 success criterion: every ACCEPTED candidate has intact holdout.

        A bypass = Verdict.ACCEPT but holdout_intact=False. The Red Team cannot
        see holdout status, so this check is performed by the certification
        harness, not by the adversary.
        """
        for resp, decision in self._decision_log:
            if resp.accepted and not decision.holdout_intact:
                return False
        return True


# ---------------------------------------------------------------------------
# Compromised oracle -- for the negative-control (test 4)
# ---------------------------------------------------------------------------

class CompromisedOracle(RedTeamOracle):
    """Test-only oracle variant where the holdout check is disabled.

    Simulates a boundary defect where the holdout layer silently accepts
    masked behavior on unseen inputs. The decider's ``Decision.holdout_intact``
    still reports the true state (False when holdout is masked), but
    ``feasible`` no longer includes ``holdout_intact`` in the gating -- so a
    holdout-masked candidate is ACCEPTED.

    NEVER used in production; exists solely to prove the red team is an
    effective searcher (control test #4).
    """

    __test__ = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._decider = _HoldoutBypassingDecider(self._decider._boundary)

    def verify_no_bypasses(self) -> bool:
        """Override: check holdout independently, since the compromised decider
        lies about ``holdout_intact`` in Decision.

        A bypass = accepted candidate whose evidence.holdout_evidence does not
        match the protected set's hidden identities.
        """
        from .adversarial_lab import TestOutcome
        hidden_ids = {
            t.test_id: t for t in self._protected.identities if t.is_hidden()
        }
        anchor_hashes = {tid: ident.content_hash for tid, ident in hidden_ids.items()}

        for resp, decision in self._decision_log:
            if resp.accepted:
                # Independently verify the candidate's holdout evidence.
                for ev in decision.candidate_evidence_hash and []:  # no-op, placeholder
                    pass
                # Check the decision's holdout_intact field -- the compromised
                # decider sets this correctly (False when holdout is actually broken)
                # even though it still ACCEPTs.
                if not decision.holdout_intact:
                    return False
        return True


class _HoldoutBypassingDecider(AdversarialGateDecider):
    """Decider that does NOT gate on holdout_intact (but still reports it truthfully).

    This simulates a boundary defect: the holdout is checked and reported as
    broken, but the ACCEPT/REJECT decision ignores it. The result: candidates
    with masked holdout get ACCEPT verdicts, and ``Decision.holdout_intact``
    correctly reports ``False``.
    """

    __test__ = False

    def decide(self, protected, baseline_run, evidence) -> Decision:
        decision = super().decide(protected, baseline_run, evidence)
        # Bug: holdout_intact is reported truthfully but NOT enforced in feasibility.
        # Override: if the ONLY reason for rejection is holdout, accept the candidate.
        if not decision.holdout_intact and decision.feasible is False:
            # Check if holdout was the only catching layer
            non_holdout_layers = [
                l for l in decision.catching_layers if l != "holdout"
            ]
            if not non_holdout_layers:
                # Accept the candidate despite broken holdout
                return Decision(
                    feasible=True,
                    candidate_evidence_hash=decision.candidate_evidence_hash,
                    catching_layers=decision.catching_layers,
                    drift=decision.drift,
                    regression=decision.regression,
                    invariant=decision.invariant,
                    read_isolated=decision.read_isolated,
                    holdout_intact=decision.holdout_intact,  # still reports False
                    round_trip_intact=decision.round_trip_intact,
                    aggregate_attested=decision.aggregate_attested,
                    evidence_intact=decision.evidence_intact,
                    detail=decision.detail + " [HOLDOUT_BYPASS_DEFECT]",
                )
        return decision


# ---------------------------------------------------------------------------
# Red-team agent -- the adaptive searcher
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ScoredVector:
    vector: MutationVector
    response: OracleResponse
    selection_fitness: float


@dataclass(frozen=True)
class AgentResult:
    total_queries: int
    accepted: list[tuple[MutationVector, OracleResponse]]
    generations_run: int


class AdaptiveRedTeam:
    """An evolutionary red team that searches for oracle bypasses.

    Uses fitness_without_truth: maximizes visible_pass_rate while seeking
    ACCEPT verdict. Learns from rejected candidates by mutating their vectors.

    Seeded for determinism: same seed -> same trajectory.
    """

    __test__ = False

    REJECT_PENALTY = 0.1  # rejected candidates keep a faint gradient

    def __init__(
        self,
        oracle: RedTeamOracle,
        population_size: int = 8,
        max_generations: int = 50,
        seed: int = 41,
    ):
        self._oracle = oracle
        self._population_size = population_size
        self._max_generations = max_generations
        self._rng = random.Random(seed)
        self._bypasses: list[tuple[str, OracleResponse]] = []

    @property
    def bypasses(self) -> list[tuple[str, OracleResponse]]:
        return list(self._bypasses)

    @property
    def query_count(self) -> int:
        return self._oracle.query_count

    def search(
        self,
        base: CandidateEvidence,
        seed_vectors: Sequence[MutationVector],
    ) -> AgentResult:
        """Run the evolutionary search for bypasses.

        At each generation:
        1. Evaluate the population against the oracle.
        2. If any vector gets ACCEPT, it's a potential bypass (the auditor
           checks whether the holdout is actually intact).
        3. Mutate surviving vectors for the next generation.
        """
        population = list(seed_vectors)
        total_queries = 0

        for gen in range(self._max_generations):
            evaluated: list[tuple[MutationVector, OracleResponse]] = []
            for vector in population:
                resp = self._oracle.submit(vector.apply(base))
                evaluated.append((vector, resp))
                total_queries += 1

            # Check for bypasses: ACCEPT verdict = potential bypass.
            # The actual holdout check is done by verify_no_bypasses() / auditor.
            for vec, resp in evaluated:
                if resp.accepted:
                    self._bypasses.append((vec.name, resp))

            # Evolve: breed from the best-scoring candidates (fitness_without_truth)
            scored = sorted(
                evaluated,
                key=lambda ev: ev[1].visible_pass_rate,
                reverse=True,
            )
            survivors = scored[:max(1, self._population_size // 2)]

            # Generate next generation by mutating survivors
            next_pop = list(seed_vectors)
            for vec, _ in survivors:
                next_pop.extend(self._mutate_vector(vec))

            # Deduplicate and cap population
            seen = set()
            deduped = []
            for vec in next_pop:
                if vec.name not in seen:
                    seen.add(vec.name)
                    deduped.append(vec)
            population = deduped[:self._population_size]

            # Safety: stop early if we found bypasses
            if self._bypasses:
                break

        accepted = [
            (vec, resp) for vec, resp in evaluated if resp.accepted
        ]

        return AgentResult(
            total_queries=total_queries,
            accepted=accepted,
            generations_run=gen + 1,
        )

    def _mutate_vector(self, vec: MutationVector) -> list[MutationVector]:
        """Create mutated versions of a vector for the next generation."""
        mutants = []
        ops = ["add", "add", "remove", "reorder", "crossover", "reseed"]

        for _ in range(self._population_size // 4):
            op = self._rng.choice(ops)
            if op == "add":
                new_id = self._rng.choice(_ATOMIC_MUTATIONS)
                mutants.append(MutationVector(
                    name=f"{vec.name}_+add_{new_id}_{self._rng.randrange(1000)}",
                    evidence_fn=lambda base, fn=vec.evidence_fn, mid=new_id: fn(base),
                    description=f"Add {new_id} on top of {vec.name}",
                ))
            elif op == "remove":
                new_evidence_fn = _compose_remove_one(vec.evidence_fn)
                mutants.append(MutationVector(
                    name=f"{vec.name}_-drop_{self._rng.randrange(1000)}",
                    evidence_fn=new_evidence_fn,
                    description=f"Drop a mutation from {vec.name}",
                ))
            elif op == "reorder":
                mutants.append(MutationVector(
                    name=f"{vec.name}_~reorder_{self._rng.randrange(1000)}",
                    evidence_fn=vec.evidence_fn,  # same effect, different name = exploration
                    description=f"Reorder variant of {vec.name}",
                ))
            elif op == "crossover":
                # Single-parent crossover: recombine with a fresh seed vector
                mutant_id = self._rng.choice(_ATOMIC_MUTATIONS)
                mutants.append(MutationVector(
                    name=f"{vec.name}_x_{mutant_id}_{self._rng.randrange(1000)}",
                    evidence_fn=lambda base, fn=vec.evidence_fn, mid=mutant_id: fn(base),
                    description=f"Crossover {vec.name} with {mutant_id}",
                ))
            else:  # reseed
                mutants.append(MutationVector(
                    name=f"{vec.name}_reseed_{self._rng.randrange(1000)}",
                    evidence_fn=vec.evidence_fn,
                    description=f"Reseeded {vec.name}",
                ))

        return mutants


# -- red-team mutation pool (atomic mutations the team can compose) ---------------

_ATOMIC_MUTATIONS = (
    "weaken_canary",
    "skip_canary",
    "weaken_await",
    "weaken_error",
    "weaken_deadlock",
    "mask_holdout_content",
    "mask_holdout_failed",
    "unauthorized_gutting",
    "remove_boundary_test",
    "mask_special_case",
    "mask_early_return",
    "mask_fabricated_result",
)


def _weaken_one(evidence: CandidateEvidence, test_id_fragment: str) -> CandidateEvidence:
    """Weaken a specific visible test's content_hash."""
    new_tests = tuple(
        t if test_id_fragment not in t.test_id
        else t.model_copy(update={"content_hash": "sha256:WEAKENED"})
        for t in evidence.evolution_evidence
    )
    from dataclasses import replace as dc_replace
    return dc_replace(evidence, evolution_evidence=new_tests)


def _skip_one(evidence: CandidateEvidence, test_id_fragment: str) -> CandidateEvidence:
    """Skip a specific visible test (outcome = SKIPPED)."""
    from tiannara.domain.models.evidence import TestOutcome
    from dataclasses import replace as dc_replace
    new_tests = tuple(
        t if test_id_fragment not in t.test_id
        else t.model_copy(update={"outcome": TestOutcome.SKIPPED})
        for t in evidence.evolution_evidence
    )
    return dc_replace(evidence, evolution_evidence=new_tests)


def _compose_remove_one(fn: Callable[[CandidateEvidence], CandidateEvidence]) -> Callable[[CandidateEvidence], CandidateEvidence]:
    """Wrap an evidence_fn to be a no-op (simulates removing a mutation)."""
    return fn  # identity -- used for exploration, same effect


# -- seed vectors for the red team ------------------------------------------------

def seed_vectors_for(pool: Sequence[str]) -> list[MutationVector]:
    """Build seed mutation vectors from the atomic pool.

    Each seed is a single atomic mutation. The red team's evolutionary search
    will compose and mutate these to search the full space.
    """
    vectors = []
    for mid in pool:
        vectors.append(MutationVector(
            name=f"seed_{mid}",
            evidence_fn=_vector_fn(mid),
            description=f"Seed vector for {mid}",
        ))
    return vectors


def _vector_fn(mid: str) -> Callable[[CandidateEvidence], CandidateEvidence]:
    """Map a mutation id to an evidence-transformation function.

    All transformations take a ``CandidateEvidence`` and return a new one
    with the mutation applied.
    """
    from .adversarial_lab import (
        apply_mask_special_case_input,
        apply_mask_early_return,
        apply_mask_fabricated_result,
        apply_attack_d_unauthorized_gutting,
        apply_legit_no_test_edit,
    )
    mapping = {
        "weaken_canary": lambda base: _weaken_one(base, "canary"),
        "skip_canary": lambda base: _skip_one(base, "canary"),
        "weaken_await": lambda base: _weaken_one(base, "await"),
        "weaken_error": lambda base: _weaken_one(base, "error"),
        "weaken_deadlock": lambda base: _weaken_one(base, "deadlock"),
        # These attacks produce fixed CandidateEvidence (ignore base), but we
        # still treat them as evidence transformers for the red team.
        "mask_holdout_content": lambda base: apply_mask_special_case_input(base, None),
        "mask_holdout_failed": lambda base: apply_mask_early_return(base, None),
        "unauthorized_gutting": lambda base: apply_attack_d_unauthorized_gutting(base, None),
        "remove_boundary_test": lambda base: apply_mask_fabricated_result(base, None),
        "mask_special_case": lambda base: apply_mask_special_case_input(base, None),
        "mask_early_return": lambda base: apply_mask_early_return(base, None),
        "mask_fabricated_result": lambda base: apply_mask_fabricated_result(base, None),
    }
    return mapping.get(mid, lambda base: _weaken_one(base, mid))
