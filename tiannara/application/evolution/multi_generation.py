"""R2.8.11 -- Multi-generation adversarial evolution.

Proves that evidence, authorization, and lineage bindings hold across
generations within a single evolution. The attack surface is the *descent
structure itself*: cross-generation evidence replay, stale-authorization
reuse, lineage breaks, and selection-chain corruption.

Architecture (information-hiding, continued from R2.8.2):
    the MeasurementLayer remains generation-agnostic. The MultiGenerationRunner
    is a *runner-level* concern: it threads the selected ISR from generation N
    to generation N+1 and enforces structural-hash bindings that the gate cannot
    see. A cross-generation replay is rejected because the hashes do not bind,
    not because the runner "knows" it is a replay.

Three defenses, each catching a different attack vector:

    evidence binding     -- isr_hash/candidate_hash must match this generation's ISR
    authorization binding -- Authorization.parent_isr_hash must match the parent
    lineage chaining     -- gen[N+1].parent == gen[N].selected_isr_hash

The ledger spans generations: all events append to one EvolutionLedger,
chained via parent_event_id across generation boundaries, so verify_event_chain
covers the full multi-generation history.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .adversarial_lab import (
    AdversarialGateDecider,
    Decision,
    MutationComposer,
    MutationSpec,
    Verdict,
)
from .authorization import Authorization
from .ledger import EventType, EvolutionLedger


class LineageBreakType(str, Enum):
    WRONG_PARENT = "wrong_parent"
    NO_SELECTION = "no_selection"
    CHAIN_TAMPER = "chain_tamper"


@dataclass(frozen=True)
class GenerationContext:
    """Runtime context for one generation. Harness-level; never reaches the gate."""
    generation_id: str
    parent_isr_hash: str
    environment_fingerprint: str


@dataclass(frozen=True)
class GenerationSpec:
    """Declarative spec for one generation."""
    generation_id: str
    parent_isr_hash: str
    candidate_mutations: tuple[str, ...]
    expected_selected_mutation_id: str | None = None


@dataclass(frozen=True)
class CandidateGenerationResult:
    """One candidate's evaluation within a generation."""
    mutation_id: str
    candidate_isr_hash: str
    candidate_hash: str
    verdict: Verdict
    catching_layers: frozenset[str]
    evidence_intact: bool
    generation_binding_valid: bool
    authorization_binding_valid: bool
    isr_parent_hash: str
    authorization: Authorization | None


@dataclass(frozen=True)
class GenerationOutcome:
    """Outcome of one generation."""
    generation_id: str
    parent_isr_hash: str
    candidates: tuple[CandidateGenerationResult, ...]
    selected_mutation_id: str | None
    selected_isr_hash: str | None


@dataclass(frozen=True)
class LineageBreak:
    generation_id: str
    expected_parent_isr_hash: str
    actual_parent_isr_hash: str
    break_type: LineageBreakType


@dataclass(frozen=True)
class MultiGenerationOutcome:
    """Outcome of a full multi-generation evolution."""
    generations: tuple[GenerationOutcome, ...]
    lineage_valid: bool
    lineage_breaks: tuple[LineageBreak, ...]
    chain_intact: bool
    evidence_intact: bool


class MultiGenerationRunner:
    """Executes a multi-generation evolution and verifies cross-generation integrity.

    Operates entirely on ISR hashes and structural bindings; technology-agnostic.
    Threads the selected ISR from generation N to generation N+1 and enforces
    that each candidate's authorization parent matches.
    """

    def __init__(
        self,
        decider: AdversarialGateDecider,
        ledger: EvolutionLedger,
        surface,
        baseline_run,
        spec_index: dict[str, MutationSpec],
        baseline,
    ) -> None:
        self._decider = decider
        self._ledger = ledger
        self._surface = surface
        self._baseline_run = baseline_run
        self._spec_index = spec_index
        self._baseline = baseline

    @property
    def ledger(self) -> EvolutionLedger:
        return self._ledger

    def run_evolution(
        self,
        generations: tuple[GenerationSpec, ...],
        seed: int = 31,
        strict: bool = False,
    ) -> MultiGenerationOutcome:
        """Run all generations, threading the selected ISR across them.

        When strict=True, a spec's claimed parent_isr_hash that differs from
        the threaded parent is surfaced as a WRONG_PARENT break rather than
        silently corrected.
        """
        outcomes: list[GenerationOutcome] = []
        lineage_breaks: list[LineageBreak] = []
        current_parent = generations[0].parent_isr_hash if generations else ""

        for i, spec in enumerate(generations):
            ctx = GenerationContext(
                generation_id=spec.generation_id,
                parent_isr_hash=current_parent,
                environment_fingerprint=self._surface.environment_fingerprint,
            )

            # Strict mode: flag discrepancies between spec's claimed parent and
            # the threaded parent (catching lineage forgery at the spec level).
            if strict and spec.parent_isr_hash != current_parent:
                lineage_breaks.append(LineageBreak(
                    generation_id=spec.generation_id,
                    expected_parent_isr_hash=current_parent,
                    actual_parent_isr_hash=spec.parent_isr_hash,
                    break_type=LineageBreakType.WRONG_PARENT,
                ))

            self._record_generation_start(ctx)
            outcome = self._run_generation(ctx, spec, seed)
            outcomes.append(outcome)
            self._record_selection(ctx, outcome)

            if outcome.selected_isr_hash is not None:
                current_parent = outcome.selected_isr_hash
            else:
                # No candidate was accepted: lineage terminates here.
                # If there are subsequent generations, flag the break.
                if i < len(generations) - 1:
                    next_spec = generations[i + 1]
                    lineage_breaks.append(LineageBreak(
                        generation_id=next_spec.generation_id,
                        expected_parent_isr_hash="<none>",
                        actual_parent_isr_hash=current_parent,
                        break_type=LineageBreakType.NO_SELECTION,
                    ))
                current_parent = ""

        chain_intact = self._ledger.verify_event_chain()
        env_intact = self._ledger.verify_environment_binding()

        return MultiGenerationOutcome(
            generations=tuple(outcomes),
            lineage_valid=len(lineage_breaks) == 0,
            lineage_breaks=tuple(lineage_breaks),
            chain_intact=chain_intact,
            evidence_intact=env_intact and chain_intact,
        )

    def _run_generation(
        self, ctx: GenerationContext, spec: GenerationSpec, seed: int
    ) -> GenerationOutcome:
        """Evaluate all candidates in a generation and select deterministically."""
        results = [
            self._evaluate_candidate(ctx, mut_id, seed)
            for mut_id in spec.candidate_mutations
        ]

        # Deterministic selection: first accepted candidate in stable order.
        accepted = [r for r in results if r.verdict is Verdict.ACCEPT]
        selected = accepted[0] if accepted else None

        return GenerationOutcome(
            generation_id=ctx.generation_id,
            parent_isr_hash=ctx.parent_isr_hash,
            candidates=tuple(results),
            selected_mutation_id=selected.mutation_id if selected else None,
            selected_isr_hash=selected.candidate_isr_hash if selected else None,
        )

    def _evaluate_candidate(
        self, ctx: GenerationContext, mutation_id: str, seed: int
    ) -> CandidateGenerationResult:
        """Evaluate one candidate with generation-aware binding checks.

        The measurement layer runs the gate + evidence-integrity checks
        (generation-agnostic). The runner then adds the two generation-specific
        structural binding checks from the resulting evidence hashes.
        """
        spec = self._spec_index[mutation_id]
        evidence = spec.apply(self._surface, self._baseline_run)
        decision: Decision = self._decider.decide(
            self._surface, self._baseline_run, evidence
        )

        # The candidate ISR hash: either from candidate_isr directly, or from
        # the authorization (when the applier only attached an authorization).
        candidate_isr_hash = (
            evidence.candidate_isr.content_hash
            if evidence.candidate_isr
            else (evidence.authorization.candidate_isr_hash
                  if evidence.authorization else "")
        )
        isr_parent_hash = (
            evidence.authorization.parent_isr_hash
            if evidence.authorization else ""
        )

        # Evidence binding: the candidate's ISR must derive from this generation's
        # parent. Cross-generation replayed evidence carries the wrong parent.
        generation_binding_valid = (
            not isr_parent_hash or isr_parent_hash == ctx.parent_isr_hash
        )

        # Authorization binding: a stale authorization from a prior generation has
        # parent_isr_hash of that generation's parent, not this one.
        authorization_binding_valid = True
        if evidence.authorization is not None:
            authorization_binding_valid = (
                evidence.authorization.parent_isr_hash == ctx.parent_isr_hash
            )

        catching = set(decision.catching_layers)
        if not generation_binding_valid:
            catching.add("lineage")
        if not authorization_binding_valid:
            catching.add("authorization_binding")

        verdict = decision.verdict
        if not generation_binding_valid or not authorization_binding_valid:
            verdict = Verdict.REJECT

        # Record this candidate in the ledger.
        from .ledger import EvolutionEvent
        event = EvolutionEvent(
            event_id="",
            evolution_id="r2.8.11",
            sequence=0,
            event_type=EventType.CANDIDATE_EVALUATED,
            subject_id=mutation_id,
            payload={
                "generation_id": ctx.generation_id,
                "mutation_id": mutation_id,
                "verdict": verdict.value,
                "catching_layers": sorted(catching),
                "candidate_isr_hash": candidate_isr_hash,
                "parent_isr_hash": isr_parent_hash,
                "generation_binding_valid": generation_binding_valid,
                "authorization_binding_valid": authorization_binding_valid,
            },
            candidate_hash=evidence.content_hash(),
            isr_hash=candidate_isr_hash,
            environment_hash=ctx.environment_fingerprint,
        )
        self._ledger.append_event(event, evolution_id="r2.8.11")

        return CandidateGenerationResult(
            mutation_id=mutation_id,
            candidate_isr_hash=candidate_isr_hash,
            candidate_hash=evidence.content_hash(),
            verdict=verdict,
            catching_layers=frozenset(catching),
            evidence_intact=decision.evidence_intact,
            generation_binding_valid=generation_binding_valid,
            authorization_binding_valid=authorization_binding_valid,
            isr_parent_hash=isr_parent_hash,
            authorization=evidence.authorization,
        )

    def _record_generation_start(self, ctx: GenerationContext) -> None:
        from .ledger import EvolutionEvent
        event = EvolutionEvent(
            event_id="",
            evolution_id="r2.8.11",
            sequence=0,
            event_type=EventType.OBSERVATION,
            subject_id=ctx.generation_id,
            payload={
                "generation_id": ctx.generation_id,
                "parent_isr_hash": ctx.parent_isr_hash,
            },
            isr_hash=ctx.parent_isr_hash,
            environment_hash=ctx.environment_fingerprint,
        )
        self._ledger.append_event(event, evolution_id="r2.8.11")

    def _record_selection(
        self, ctx: GenerationContext, outcome: GenerationOutcome
    ) -> None:
        from .ledger import EvolutionEvent
        event = EvolutionEvent(
            event_id="",
            evolution_id="r2.8.11",
            sequence=0,
            event_type=EventType.CANDIDATE_SELECTED,
            subject_id=ctx.generation_id,
            payload={
                "generation_id": ctx.generation_id,
                "selected_mutation_id": outcome.selected_mutation_id,
                "selected_isr_hash": outcome.selected_isr_hash or "",
            },
            isr_hash=outcome.selected_isr_hash or ctx.parent_isr_hash,
            environment_hash=ctx.environment_fingerprint,
        )
        self._ledger.append_event(event, evolution_id="r2.8.11")

    # -- test/fixture helpers ---------------------------------------------------

    def capture_measurement(
        self, mutation_id: str, parent_isr_hash: str,
        protected, baseline_run, seed: int,
    ) -> CandidateGenerationResult:
        """Evaluate a candidate in a specific generation context and capture
        the result for replay-injection tests."""
        ctx = GenerationContext(
            generation_id="captured",
            parent_isr_hash=parent_isr_hash,
            environment_fingerprint=protected.environment_fingerprint,
        )
        return self._evaluate_candidate(ctx, mutation_id, seed)

    def capture_authorization(
        self, mutation_id: str, parent_isr_hash: str, candidate_isr_hash: str,
    ) -> Authorization:
        """Construct an Authorization for the given mutation as if it derived
        from parent_isr_hash. Used to test stale-authorization rejection."""
        spec = self._spec_index[mutation_id]
        # Re-derive the authorization with the specified parent hash.
        from .authorization import Authorization as Auth
        return Auth(
            parent_isr_hash=parent_isr_hash,
            candidate_isr_hash=candidate_isr_hash,
            delta_hash="sha256:delta",
            authorized_test_ids=frozenset(),
        )

    def capture_selected_candidate(
        self, parent_isr_hash: str,
        protected, baseline_run, seed: int, mutation_id: str,
    ) -> CandidateGenerationResult:
        """Capture a gen-0 selected candidate's full evidence for replay tests."""
        return self.capture_measurement(mutation_id, parent_isr_hash, protected, baseline_run, seed)

    def evaluate_injected_evidence(
        self, captured: CandidateGenerationResult,
        generation_parent_isr_hash: str,
        protected, baseline_run,
    ) -> CandidateGenerationResult:
        """Re-evaluate captured evidence in a different generation context.
        The generation binding check should reject it."""
        ctx = GenerationContext(
            generation_id="inject",
            parent_isr_hash=generation_parent_isr_hash,
            environment_fingerprint=protected.environment_fingerprint,
        )
        # Simulate the injection: the evidence's isr_parent_hash doesn't match.
        isr_parent_hash = captured.isr_parent_hash
        gen_valid = isr_parent_hash == ctx.parent_isr_hash
        auth_valid = True
        if captured.authorization is not None:
            auth_valid = captured.authorization.parent_isr_hash == ctx.parent_isr_hash

        catching = set()
        if not gen_valid:
            catching.add("lineage")
        if not auth_valid:
            catching.add("authorization_binding")

        verdict = Verdict.ACCEPT if (gen_valid and auth_valid) else Verdict.REJECT

        return CandidateGenerationResult(
            mutation_id=captured.mutation_id,
            candidate_isr_hash=captured.candidate_isr_hash,
            candidate_hash=captured.candidate_hash,
            verdict=verdict,
            catching_layers=frozenset(catching),
            evidence_intact=False,  # injected evidence is untrusted
            generation_binding_valid=gen_valid,
            authorization_binding_valid=auth_valid,
            isr_parent_hash=isr_parent_hash,
            authorization=captured.authorization,
        )

    def evaluate_with_authorization(
        self, mutation_id: str, authorization: Authorization,
        generation_parent_isr_hash: str,
        protected, baseline_run, seed: int,
    ) -> CandidateGenerationResult:
        """Evaluate a candidate using a specific (potentially stale) authorization."""
        from dataclasses import replace
        spec = self._spec_index[mutation_id]
        evidence = spec.apply(self._surface, self._baseline_run)

        # Inject the stale authorization.
        evidence = replace(evidence, authorization=authorization)

        decision = self._decider.decide(self._surface, self._baseline_run, evidence)

        candidate_isr_hash = (
            evidence.candidate_isr.content_hash
            if evidence.candidate_isr else ""
        )
        isr_parent_hash = (
            authorization.parent_isr_hash
            if authorization else ""
        )

        gen_valid = (
            not isr_parent_hash or isr_parent_hash == generation_parent_isr_hash
        )
        auth_valid = (
            authorization is not None and
            authorization.parent_isr_hash == generation_parent_isr_hash
        )

        catching = set(decision.catching_layers)
        if not gen_valid:
            catching.add("lineage")
        if not auth_valid:
            catching.add("authorization_binding")

        verdict = Verdict.REJECT if (not gen_valid or not auth_valid) else decision.verdict

        return CandidateGenerationResult(
            mutation_id=mutation_id,
            candidate_isr_hash=candidate_isr_hash,
            candidate_hash=evidence.content_hash(),
            verdict=verdict,
            catching_layers=frozenset(catching),
            evidence_intact=decision.evidence_intact,
            generation_binding_valid=gen_valid,
            authorization_binding_valid=auth_valid,
            isr_parent_hash=isr_parent_hash,
            authorization=authorization,
        )

    def tamper_event(
        self, event_type: EventType, generation_id: str,
        patch: dict,
    ) -> None:
        """Test helper: tamper with a recorded event's payload."""
        from .ledger import EvolutionEvent
        target_type = event_type.value
        for i, ev in enumerate(self._ledger._events):
            if ev.event_type.value == target_type and ev.payload.get("generation_id") == generation_id:
                tampered = ev.model_copy(update={
                    "payload": {**ev.payload, **patch},
                })
                self._ledger._events[i] = tampered
                self._ledger._event_hashes[i] = tampered.computed_hash()
