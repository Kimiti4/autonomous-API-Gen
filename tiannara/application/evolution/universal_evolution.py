"""R2.10.5 — UniversalEvolutionLoop: universal evolutionary search.

R2.9 proved population dynamics on the FSM substrate; R2.10.4 proved the
universal semantic transaction (>= 4 independent genes across distinct
domains under one gate). R2.10.5 fuses them: multi-generation search whose
final selected ISR is reconstructable BYTE-EXACTLY from the ledger alone —
replaying only the recorded delta material (each recorded generation event
carries the full canonical content of every edit).

Two invariants, locked before implementation:

  1. IdentityIndex is a DERIVED PROJECTION: a frozen dataclass with no
     mutation surface, constructible only through ``derive(isr)``. The ISR
     is the source of truth; the index is a deterministic projection of it.
     Gene replacement lives at module level (``identity_index_replace_gene``)
     and produces a new ISR version.
  2. Parent-authoritativeness is PER-STEP: each generation is judged by that
     generation's parent constitution (``resolve_evolution_policy(parent)``),
     never by rules the candidate authored. A governance-authorized policy
     change may propagate to the next generation; self-weakening within a
     generation is rejected by the protection projection.

Mechanism, not measurement: the selector's per-objective engagement proxy
(the delta edits >= 1 subject gene of an objective) proves the lexicographic
tier mechanism only — no objective is measured here (the R2.8 evidence
substrate determines measurement, and this module holds no evaluation
machinery of its own, structurally).
"""
from __future__ import annotations

import dataclasses
import random
import types
from dataclasses import dataclass, is_dataclass
from enum import Enum
from typing import (
    Any,
    Callable,
    Mapping,
    Optional,
    Sequence,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)

from constitutional_architecture.isr.model import (
    AcceptanceCriterion,
    ArchitecturalBoundary,
    BusinessCapability,
    DataMigrationIntent,
    DeploymentIntent,
    DocumentationIntent,
    ReliabilityRequirement,
    Requirement,
    TemporalConstraint,
    TestingAnchor,
    Workflow,
)
from constitutional_architecture.isr.semantics.evolution_policy import (
    ObjectiveTier,
)
from constitutional_architecture.isr.semantics.projection import (
    CanonicalizationError,
)

from .identity_index import IdentityIndex
from .ledger import stable_isr_hash
from .semantic_evolution_gate import (
    GeneEdit,
    MultiGeneDelta,
    apply_multi_gene_delta,
    resolve_evolution_policy,
)

MINIMUM_COMPOSITION_DOMAINS = 4


# -- generation / run records --------------------------------------------------

@dataclass(frozen=True)
class GenerationRecord:
    """One generation's decision, as recorded in the ledger.

    ``selected_delta`` is None when the generation halted honestly (no
    feasible candidate). The parent hash + selected delta + selected
    candidate hash make the lineage chain reconstructable end to end.
    """

    generation: int
    parent_semantic_hash: str
    selected_delta: Optional[MultiGeneDelta]
    selected_candidate_hash: Optional[str]
    policy_resolved_from: str
    feasible_count: int
    population_size: int


@dataclass(frozen=True)
class UniversalEvolutionResult:
    """The outcome of one universal-search run.

    ``reconstructable`` is the R2.10.5 headline: True iff replaying the
    ledger's recorded delta material from the initial ISR reproduces the
    final selected ISR byte-exactly (same semantic hash) with an intact
    identity namespace.
    """

    final_isr_semantic_hash: str
    generations_run: int
    lineage: tuple[GenerationRecord, ...]
    reconstructable: bool


# -- variation -----------------------------------------------------------------

class UniversalVariationOperator:
    """Generate a population of universal deltas from one parent ISR.

    Each delta composes >= 4 independent gene edits across >= 4 distinct
    domains (the R2.10.4 composition minimum), drawn deterministically from
    ``random.Random(seed)``. The identity namespace is derived from the
    parent; only domains with a declared mutator participate. Mutators are
    application-layer callables ``(gene, rng) -> new gene`` — the operator
    is mechanism, never content.
    """

    def __init__(
        self,
        identity_index: Any = None,
        domain_mutators: Optional[Mapping[str, Callable]] = None,
    ) -> None:
        self._identity_index = identity_index or IdentityIndex
        self._domain_mutators = dict(domain_mutators or {})

    def generate(
        self, parent_isr: Any, population_size: int, seed: int
    ) -> list[MultiGeneDelta]:
        index = self._identity_index.derive(parent_isr)
        by_domain = index.genes_by_domain()
        mutable = sorted(
            domain for domain in by_domain if domain in self._domain_mutators
        )
        if len(mutable) < MINIMUM_COMPOSITION_DOMAINS:
            raise ValueError(
                "universal variation needs >= 4 mutable domains "
                f"(got {len(mutable)}: {mutable})"
            )
        rng = random.Random(seed)
        population = []
        for i in range(population_size):
            population.append(self._generate_one(by_domain, mutable, rng, i))
        return population

    def _generate_one(
        self,
        by_domain: Mapping[str, tuple[tuple[str, Any], ...]],
        mutable: Sequence[str],
        rng: random.Random,
        index: int,
    ) -> MultiGeneDelta:
        chosen = rng.sample(mutable, k=MINIMUM_COMPOSITION_DOMAINS)
        edits = []
        for domain in sorted(chosen):
            gene_id, gene = rng.choice(by_domain[domain])
            edits.append(
                GeneEdit(domain, gene_id, self._domain_mutators[domain](gene, rng))
            )
        return MultiGeneDelta(f"universal-{index:03d}", tuple(edits))


# -- lexicographic tiers + selection -------------------------------------------

def lexicographic_tiers(parent_isr: Any) -> tuple[str, ...]:
    """The objective evaluation order — never a scalar, never a weighted sum.

    CONSTITUTIONAL objectives (the hard presence gate) come first, then
    OPTIMIZATION objectives by (priority, weight descending, objective_id).
    Resolved from the PARENT constitution (``resolve_evolution_policy``),
    per-step parent-authoritative.
    """
    policy = resolve_evolution_policy(parent_isr)
    by_id = {o.objective_id: o for o in parent_isr.system.evolution_objectives}
    ordered = sorted(
        (by_id[ref] for ref in policy.objective_refs if ref in by_id),
        key=lambda o: (
            0 if o.tier is ObjectiveTier.CONSTITUTIONAL else 1,
            o.priority,
            -o.weight,
            o.objective_id,
        ),
    )
    return tuple(o.objective_id for o in ordered)


class UniversalSelector:
    """Deterministic lexicographic selection over a proxy profile.

    Per objective (in tier order), the proxy is 1 iff the delta edits >= 1
    subject gene of that objective — engagement, not measurement. The
    profile is ALWAYS a tuple (never a scalar), compared lexicographically;
    ties break deterministically by delta_id. Operates on the PARENT
    constitution only.
    """

    def select(self, feasible: Sequence, parent_isr: Any):
        """``feasible`` is a sequence of (candidate_isr, delta) pairs;
        returns the winning pair."""
        objectives_by_id = {
            o.objective_id: o for o in parent_isr.system.evolution_objectives
        }
        tiers = lexicographic_tiers(parent_isr)

        def profile(delta: MultiGeneDelta) -> tuple[int, ...]:
            edited_gene_ids = {gene_id for _, gene_id in delta.edited_genes}
            return tuple(
                1 if set(objectives_by_id[tier].subject_refs) & edited_gene_ids else 0
                for tier in tiers
            )

        return max(
            feasible,
            key=lambda pair: (profile(pair[1]), pair[1].delta_id),
        )


# -- canonical-form rebuild (the ledger replay surface) ------------------------

_GENE_TYPES: dict[str, type] = {
    "capability": BusinessCapability,
    "requirement": Requirement,
    "acceptance_criterion": AcceptanceCriterion,
    "boundary": ArchitecturalBoundary,
    "testing_anchor": TestingAnchor,
    "reliability": ReliabilityRequirement,
    "deployment": DeploymentIntent,
    "documentation": DocumentationIntent,
    "migration": DataMigrationIntent,
    "temporal": TemporalConstraint,
    "behavior": Workflow,
}


def rebuild_gene(domain: str, content: dict) -> Any:
    """Rebuild one gene dataclass from its canonical form — the exact
    inverse of ``canonical_form`` for the ten identity domains. This is the
    surface that makes the R2.10.5 headline possible: recorded canonical
    content is sufficient to reconstruct every edited gene, byte-exactly.
    """
    try:
        gene_type = _GENE_TYPES[domain]
    except KeyError:
        raise KeyError(f"no rebuild surface for domain '{domain}'") from None
    return _rebuild(gene_type, content)


def _rebuild(gene_type: type, data: dict) -> Any:
    hints = get_type_hints(gene_type)
    kwargs: dict[str, Any] = {}
    for f in dataclasses.fields(gene_type):
        if f.name not in data:
            if f.default is not dataclasses.MISSING:
                kwargs[f.name] = f.default
            elif f.default_factory is not dataclasses.MISSING:
                kwargs[f.name] = f.default_factory()
            else:
                raise CanonicalizationError(
                    f"field '{f.name}' absent from canonical content "
                    f"of {gene_type.__name__}"
                )
            continue
        kwargs[f.name] = _rebuild_value(hints[f.name], data[f.name])
    return gene_type(**kwargs)


def _rebuild_value(expected_type: Any, value: Any) -> Any:
    origin = get_origin(expected_type)
    if origin is Union or origin is types.UnionType:
        members = [m for m in get_args(expected_type) if m is not type(None)]
        return _rebuild_value(members[0], value)
    if origin is tuple:
        (item_type, _) = get_args(expected_type)  # tuple[X, ...] -> (X, Ellipsis)
        return tuple(_rebuild_value(item_type, item) for item in value)
    if origin is list:
        (item_type,) = get_args(expected_type)
        return [_rebuild_value(item_type, item) for item in value]
    if origin is dict:
        (_, value_type) = get_args(expected_type)
        return {key: _rebuild_value(value_type, item) for key, item in value.items()}
    if isinstance(expected_type, type) and is_dataclass(expected_type):
        return _rebuild(expected_type, value)
    if isinstance(expected_type, type) and issubclass(expected_type, Enum):
        # canonical form of a (str, Enum) is the enum object itself — the
        # projection's str branch catches it before the Enum branch — so the
        # replay value is the enum (in-memory) or its string value (durable).
        return expected_type(value)
    if expected_type is float:
        return float(value)  # canonical floats are repr() — exact round-trip
    if expected_type is int:
        return int(value)
    if expected_type is bool:
        return bool(value)
    if expected_type is str:
        return str(value)
    raise CanonicalizationError(f"no rebuild path for {expected_type}")


# -- the loop ------------------------------------------------------------------

class UniversalEvolutionLoop:
    """Multi-generation universal search over the semantic ISR.

    Each generation: vary the parent into a population of universal deltas,
    judge every candidate under the PARENT's constitution (feasibility
    first, then the four proofs), select deterministically, record the
    generation (full canonical delta content) in the ledger, and advance.
    Halts honestly when a generation yields no feasible candidate. The
    final ISR must be reconstructable byte-exactly from the ledger's
    recorded delta material.
    """

    def __init__(
        self,
        variation: Any,
        semantic_gate: Any,
        selector: Any,
        ledger: Any,
        identity_index: Any = None,
        authorization: Any = None,
    ) -> None:
        self._variation = variation
        self._gate = semantic_gate
        self._selector = selector
        self._ledger = ledger
        self._identity_index = identity_index or IdentityIndex
        self._authorization = authorization
        self._current_generation = 0

    # -- the run ---------------------------------------------------------------

    def run(
        self,
        initial_isr: Any,
        generations: int,
        population_size: int,
        seed: int,
    ) -> UniversalEvolutionResult:
        current = initial_isr
        lineage: list[GenerationRecord] = []
        self._run_evolution_id = f"universal-run-{seed}"
        recorded_before = len(self._ledger.recorded_deltas())
        for generation in range(generations):
            self._current_generation = generation
            population = self._variation.generate(
                current, population_size, seed + generation
            )
            record = self._run_generation(current, population, generation)
            if record.selected_delta is None:
                break  # halt honestly: nothing feasible this generation
            lineage.append(record)
            current = self._apply(current, record.selected_delta, 0)
        final_hash = stable_isr_hash(current)
        recorded = self._ledger.recorded_deltas()[recorded_before:]
        reconstructable = self._verify_reconstruction(
            initial_isr, recorded, final_hash
        )
        return UniversalEvolutionResult(
            final_hash, len(lineage), tuple(lineage), reconstructable
        )

    # -- the application seam (judged by the gate, like any application layer) --

    def _apply(self, parent: Any, delta: MultiGeneDelta, seed: int):
        return self._gate._apply(parent, delta, seed)

    def _run_generation(
        self,
        parent: Any,
        population: Sequence[MultiGeneDelta],
        generation: int,
    ) -> GenerationRecord:
        feasible: list = []
        for delta in population:
            candidate = self._apply(parent, delta, 0)
            verdict = self._gate.evaluate_candidate(
                parent, candidate, delta, 0, authorization=self._authorization
            )
            if verdict.feasible:
                feasible.append((candidate, delta))
        if not feasible:
            return GenerationRecord(
                generation,
                stable_isr_hash(parent),
                None,
                None,
                "parent",
                0,
                len(population),
            )
        candidate, delta = self._selector.select(feasible, parent)
        record = GenerationRecord(
            generation,
            stable_isr_hash(parent),
            delta,
            stable_isr_hash(candidate),
            "parent",
            len(feasible),
            len(population),
        )
        self._ledger.record_generation(
            record, evolution_id=self._run_evolution_id
        )
        return record

    # -- the R2.10.5 headline: byte-exact reconstruction from the ledger --------

    def _verify_reconstruction(
        self, initial_isr: Any, deltas: Sequence[dict], final_hash: str
    ) -> bool:
        """Replay the recorded delta material from the initial ISR and
        require a byte-exact (hash-identical) final ISR whose identity
        namespace is intact (every gene present, no dangling reference)."""
        current = initial_isr
        for material in deltas:
            current = self._replay_delta(current, material)
        if stable_isr_hash(current) != final_hash:
            return False
        index = self._identity_index.derive(current)
        return bool(index.genes) and index.dangling_references == ()

    @staticmethod
    def _replay_delta(current: Any, material: dict) -> Any:
        edits = tuple(
            GeneEdit(
                edit["domain"],
                edit["gene_id"],
                rebuild_gene(edit["domain"], edit["new_gene"]),
            )
            for edit in material["edits"]
        )
        return apply_multi_gene_delta(
            current, MultiGeneDelta(material["delta_id"], edits)
        )