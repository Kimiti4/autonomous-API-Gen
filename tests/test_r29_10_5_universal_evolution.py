"""R2.10.5 — UniversalEvolutionLoop: universal evolutionary search.

R2.9 proved population dynamics on the FSM substrate; R2.10.4 proved the
universal semantic transaction (>= 4 independent genes across distinct
domains under one gate). R2.10.5 fuses them: multi-generation search whose
final selected ISR is reconstructable BYTE-EXACTLY from the ledger alone —
replaying only the recorded delta material (each recorded generation event
carries the full canonical content of every edit).

The acceptance evidence:

  1.  the final selected ISR is reconstructable byte-exactly from the
      ledger alone (in-memory AND after durable reload);
  2.  the lineage chain is intact — every recorded generation's parent
      hash precedes its own selected candidate hash;
  3.  locality holds in EVERY generation (exactly the declared genes
      move, nothing else);
  4.  cross-gene reference integrity holds in every generation;
  5.  parent-authoritativeness holds in every generation (behavioral
      records + the source resolves policy from the parent only);
  6.  a candidate that weakens its OWN evolution-policy carriers is
      rejected within the generation — the search halts honestly;
  7.  a governance-authorized policy change propagates across
      generations and governs the next generation's search;
  8.  the E/H carriers (boundaries, testing anchors) stay byte-identical
      across the whole search;
  9.  the R2.8 evidence substrate is the ONLY trust boundary (the scan
      now covers universal_evolution.py itself, and the search imports
      no evaluation machinery);
  10. candidate identity is deterministic — same seed, same population,
      same winners, same ledger content;
  11. competing candidates compare deterministically — the profile is a
      tuple (never a scalar), compared lexicographically with a
      deterministic tie-break;
  12. the identity index is a derived projection — frozen, no mutation
      surface, derive-only construction, module-level replacement;
  13. diversity is observed over universal genes (entropy > 0) without
      ever influencing selection;
  14. an all-infeasible run halts honestly (generations_run == 0,
      reconstructable True, nothing recorded);
  15. Option A (twelfth use) — no new carriers, no matrix movement:
      the recipe ISR hash is unchanged and the matrix stays 12/18/0/0.
"""
from __future__ import annotations

import ast
import dataclasses
import inspect
import pathlib
import tempfile
from types import SimpleNamespace

import pytest

from constitutional_architecture.governance.constitutional_authorization import (
    ConstitutionalAuthorizationRegistry,
)
from constitutional_architecture.isr.model import (
    CompatibilityPolicy,
    DocumentationAudience,
    DocumentationPurpose,
    EvolutionPolicy,
    ProtectedRegion,
    ProtectionKind,
    RolloutStrategy,
)
from tiannara.application.evolution.diversity import DiversityObserver
from tiannara.application.evolution.identity_index import (
    IdentityIndex,
    identity_index_replace_gene,
)
from tiannara.application.evolution.ledger import (
    EvolutionLedger,
    stable_isr_hash,
)
from tiannara.application.evolution.protection import (
    SELF_GOVERNANCE_REF,
    EvolutionProtectionEvaluator,
)
from tiannara.application.evolution.semantic_evolution_gate import (
    GeneEdit,
    MultiGeneDelta,
    SemanticEvolutionGate,
    apply_multi_gene_delta,
    is_projection_consumed_by_r28,
)
from tiannara.application.evolution.universal_evolution import (
    UniversalEvolutionLoop,
    UniversalEvolutionResult,
    UniversalSelector,
    UniversalVariationOperator,
    lexicographic_tiers,
    rebuild_gene,
)
from .test_r29_10_1_capability_audit import RECIPE
from .test_r29_10_4_semantic_evolution_gate import (
    SemanticEvolutionIntegrationHarness,
)


# =============================================================================
# The harness: deterministic, lint-clean universal variation
# =============================================================================

# Every free-text vocabulary below is mechanism-lint clean (no term from the
# eight MECHANISM_TERMS sets appears in any scanned field), and every mutator
# picks a value != the gene's current one so each edit is a REAL semantic
# change (locality can then detect any disturbance).
_CAPABILITY_INTENTS = (
    "process a payment with dispute resolution",
    "process a payment with audit logging",
    "process a payment with settlement reconciliation",
    "process a payment with customer notification",
    "process a payment with chargeback handling",
)
_REQUIREMENT_STATEMENTS = (
    "payments must complete within one business day and be traceable",
    "payments must complete within one business day and be reversible",
    "payments must complete within one business day and be idempotent",
)
_CRITERION_OBLIGATIONS = (
    "payments must complete within one business day and be traceable",
    "payments must complete within one business day and be reversible",
    "payments must complete within one business day and be idempotent",
)
_RELIABILITY_DURATIONS = (2000, 3000, 4000, 6000, 8000)
_DEPLOYMENT_STRATEGIES = (
    RolloutStrategy.BLUE_GREEN,
    RolloutStrategy.PROGRESSIVE,
    RolloutStrategy.IMMEDIATE,
)
_DOCUMENTATION_PURPOSES = (
    DocumentationPurpose.ARCHITECTURAL_RATIONALE,
    DocumentationPurpose.API_CONTRACT,
    DocumentationPurpose.ONBOARDING,
    DocumentationPurpose.COMPLIANCE,
)
_DOCUMENTATION_AUDIENCES = (
    DocumentationAudience.ARCHITECT,
    DocumentationAudience.SECURITY_AUDITOR,
    DocumentationAudience.END_USER,
)
_MIGRATION_COMPAT = (
    CompatibilityPolicy.FORWARD,
    CompatibilityPolicy.BIDIRECTIONAL,
    CompatibilityPolicy.BREAKING,
)
_TEMPORAL_DURATIONS = (350, 400, 500, 600)
_BEHAVIOR_DESCRIPTIONS = (
    "handles a payment with a retry boundary",
    "handles a payment with settlement reconciliation",
    "handles a payment with customer notification",
    "handles a payment with chargeback handling",
)


def _pick(rng, options, current):
    pool = tuple(o for o in options if o != current)
    return rng.choice(pool)


def domain_mutators() -> dict:
    """Nine deterministic mutators (boundary / testing_anchor excluded so
    the E/H carriers stay byte-identical across the whole search)."""
    return {
        "capability": lambda gene, rng: dataclasses.replace(
            gene, intent=_pick(rng, _CAPABILITY_INTENTS, gene.intent)
        ),
        "requirement": lambda gene, rng: dataclasses.replace(
            gene, statement=_pick(rng, _REQUIREMENT_STATEMENTS, gene.statement)
        ),
        "acceptance_criterion": lambda gene, rng: dataclasses.replace(
            gene, obligation=_pick(rng, _CRITERION_OBLIGATIONS, gene.obligation)
        ),
        "reliability": lambda gene, rng: dataclasses.replace(
            gene,
            recovery_objectives=(
                dataclasses.replace(
                    gene.recovery_objectives[0],
                    max_recovery_duration_ms=_pick(
                        rng, _RELIABILITY_DURATIONS,
                        gene.recovery_objectives[0].max_recovery_duration_ms,
                    ),
                ),
            ),
        ),
        "deployment": lambda gene, rng: dataclasses.replace(
            gene, rollout_strategy=_pick(rng, _DEPLOYMENT_STRATEGIES, gene.rollout_strategy)
        ),
        "documentation": lambda gene, rng: dataclasses.replace(
            gene,
            purpose=_pick(rng, _DOCUMENTATION_PURPOSES, gene.purpose),
            audience=_pick(rng, _DOCUMENTATION_AUDIENCES, gene.audience),
        ),
        "migration": lambda gene, rng: dataclasses.replace(
            gene,
            compatibility_policy=_pick(
                rng, _MIGRATION_COMPAT, gene.compatibility_policy
            ),
        ),
        "temporal": lambda gene, rng: dataclasses.replace(
            gene, duration_ms=_pick(rng, _TEMPORAL_DURATIONS, gene.duration_ms)
        ),
        "behavior": lambda gene, rng: dataclasses.replace(
            gene, description=_pick(rng, _BEHAVIOR_DESCRIPTIONS, gene.description)
        ),
    }


class PopulationMember:
    """The diversity observer's adapter shape over a universal population:
    candidate_isr + operator_id + mutation_delta.entries (the identity of
    the delta, never its evaluation)."""

    def __init__(self, candidate_isr, operator_id, delta) -> None:
        self.candidate_isr = candidate_isr
        self.operator_id = operator_id
        self.mutation_delta = SimpleNamespace(
            entries=tuple(sorted(delta.edited_genes))
        )


class UniversalEvolutionHarness:
    def __init__(
        self,
        authority=None,
        authorization=None,
        loop_type=UniversalEvolutionLoop,
    ) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name
        self.ledger = EvolutionLedger(root=self.root)
        self.gate = SemanticEvolutionGate(
            identity_index=IdentityIndex,
            protection=EvolutionProtectionEvaluator(authority=authority),
            ledger=self.ledger,
        )
        self.variation = UniversalVariationOperator(
            identity_index=IdentityIndex,
            domain_mutators=domain_mutators(),
        )
        self.selector = UniversalSelector()
        self.loop = loop_type(
            variation=self.variation,
            semantic_gate=self.gate,
            selector=self.selector,
            ledger=self.ledger,
            identity_index=IdentityIndex,
            authorization=authorization,
        )
        self._base = SemanticEvolutionIntegrationHarness()

    def parent_isr(self):
        return self._base.parent_isr()

    def run(self, seed: int = 7, generations: int = 3, population_size: int = 4):
        return self.loop.run(self.parent_isr(), generations, population_size, seed)

    def replay(self, initial, deltas):
        """Independent replay of the recorded delta material through the
        PUBLIC surface (rebuild_gene + apply_multi_gene_delta)."""
        current = initial
        for material in deltas:
            edits = tuple(
                GeneEdit(
                    edit["domain"],
                    edit["gene_id"],
                    rebuild_gene(edit["domain"], edit["new_gene"]),
                )
                for edit in material["edits"]
            )
            current = apply_multi_gene_delta(
                current, MultiGeneDelta(material["delta_id"], edits), 0
            )
        return current


@pytest.fixture
def harness() -> UniversalEvolutionHarness:
    return UniversalEvolutionHarness()


# -- application-layer seams (the loop's _apply is judged by the gate) ---------

class WeakeningEvolutionLoop(UniversalEvolutionLoop):
    """An application layer that strips its own evolution-policy carriers
    from generation 1 onward. The gate must reject every such candidate
    (self-governance, CONSTITUTIONAL) and the search must halt honestly."""

    def _apply(self, parent, delta, seed):
        candidate = super()._apply(parent, delta, seed)
        if self._current_generation >= 1:
            candidate = candidate.with_system(
                dataclasses.replace(
                    candidate.system,
                    evolution_objectives=(),
                    protected_regions=(),
                    evolution_policies=(),
                )
            )
        return candidate


# =============================================================================
# 1.  Reconstructable from the ledger alone
# =============================================================================

def test_final_selected_isr_reconstructable_from_ledger(harness):
    """The R2.10.5 headline: replaying ONLY the ledger's recorded delta
    material from the initial ISR reproduces the final selected ISR
    byte-exactly — in memory and after durable reload (the record chain
    survives instance restarts)."""
    result = harness.run(seed=7, generations=3, population_size=4)
    assert isinstance(result, UniversalEvolutionResult)
    assert result.reconstructable is True
    assert result.generations_run == 3
    assert result.lineage

    initial = harness.parent_isr()
    replayed = harness.replay(initial, harness.ledger.recorded_deltas())
    assert stable_isr_hash(replayed) == result.final_isr_semantic_hash
    assert harness.ledger.verify_event_chain() is True

    reloaded = EvolutionLedger.load(harness.root)
    assert reloaded.verify_event_chain() is True
    durable = harness.replay(initial, reloaded.recorded_deltas())
    assert stable_isr_hash(durable) == result.final_isr_semantic_hash
    assert len(reloaded.recorded_deltas()) == result.generations_run


# =============================================================================
# 2.  Lineage chain intact
# =============================================================================

def test_lineage_chain_intact(harness):
    """Every recorded generation's parent hash precedes its own selected
    candidate hash; the final recorded candidate IS the final ISR."""
    result = harness.run(seed=7, generations=3, population_size=4)
    current = harness.parent_isr()
    for i, record in enumerate(result.lineage):
        assert record.generation == i
        assert record.policy_resolved_from == "parent"
        assert record.parent_semantic_hash == stable_isr_hash(current)
        assert record.selected_delta is not None
        current = apply_multi_gene_delta(current, record.selected_delta, 0)
        assert record.selected_candidate_hash == stable_isr_hash(current)
    assert stable_isr_hash(current) == result.final_isr_semantic_hash


# =============================================================================
# 3.  Locality in every generation
# =============================================================================

def test_locality_holds_every_generation(harness):
    """Each replayed generation moves EXACTLY the declared genes — the
    identity-index hashes (one namespace, derived per ISR) agree."""
    result = harness.run(seed=7, generations=3, population_size=4)
    current = harness.parent_isr()
    for record in result.lineage:
        before = IdentityIndex.derive(current).gene_hashes
        current = apply_multi_gene_delta(current, record.selected_delta, 0)
        after = IdentityIndex.derive(current).gene_hashes
        moved = {key for key in before if before[key] != after.get(key)}
        assert moved == record.selected_delta.edited_genes


# =============================================================================
# 4.  Cross-gene reference integrity in every generation
# =============================================================================

def test_reference_integrity_holds_every_generation(harness):
    """Every replayed generation's parent and candidate leave the identity
    namespace intact — no new dangling cross-gene reference anywhere."""
    result = harness.run(seed=7, generations=3, population_size=4)
    current = harness.parent_isr()
    assert IdentityIndex.derive(current).dangling_references == ()
    for record in result.lineage:
        current = apply_multi_gene_delta(current, record.selected_delta, 0)
        assert IdentityIndex.derive(current).dangling_references == ()


# =============================================================================
# 5.  Parent-authoritative every generation
# =============================================================================

def test_parent_authoritative_every_generation(harness):
    """Behavioral: every recorded generation resolves the governing policy
    from its PARENT. Structural: the search source calls the policy
    resolution with the parent only — never with a candidate."""
    result = harness.run(seed=7, generations=3, population_size=4)
    assert all(r.policy_resolved_from == "parent" for r in result.lineage)

    source = pathlib.Path(inspect.getfile(UniversalEvolutionLoop)).read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)
    calls = [
        ast.unparse(node)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "resolve_evolution_policy"
    ]
    assert calls
    assert all("parent" in call for call in calls)
    assert not any("candidate" in call for call in calls)


# =============================================================================
# 6.  Self-weakening within a generation is rejected
# =============================================================================

def test_self_weakening_within_generation_rejected():
    """An application layer that strips its own evolution-policy carriers
    from generation 1 onward produces NOTHING feasible: the self-governance
    seam (CONSTITUTIONAL) rejects every such candidate and the search halts
    honestly with a reconstructable lineage of what DID happen."""
    harness = UniversalEvolutionHarness(loop_type=WeakeningEvolutionLoop)
    result = harness.run(seed=7, generations=3, population_size=4)
    assert result.generations_run == 1
    assert len(result.lineage) == 1
    assert result.lineage[0].generation == 0
    assert result.reconstructable is True
    recorded = harness.ledger.recorded_deltas()
    assert len(recorded) == 1  # only the selected generation is recorded
    assert stable_isr_hash(harness.replay(harness.parent_isr(), recorded)) == (
        result.final_isr_semantic_hash
    )


# =============================================================================
# 7.  Authorized policy change propagates across generations
# =============================================================================

def test_authorized_policy_change_propagates_across_generations():
    """(a) THE seam: a governance-issued authorization (region_ref
    'self_governance' covering the carrier path) makes a constitutional
    change feasible; without it the SAME change is rejected (CONSTITUTIONAL,
    self-governance notes name the weakening). (b) Propagation: the
    authorized change becomes the next search's constitution — a search
    launched from the changed parent is governed by the new region and
    halts honestly at generation 0."""
    authority = ConstitutionalAuthorizationRegistry()
    authorization = authority.issue(
        authorization_id="auth-r2.10.5-self-governance",
        region_ref=SELF_GOVERNANCE_REF,
        subject_refs=("system.protected_regions[0]",),
        rationale="governance-reviewed constitutional change",
        authorizer="governance-kernel",
    )
    base = SemanticEvolutionIntegrationHarness()
    parent = base.parent_isr()
    delta = base.four_gene_delta()
    candidate = base.gate._apply(parent, delta, seed=7)
    rewritten = candidate.with_system(
        dataclasses.replace(
            candidate.system,
            protected_regions=(
                ProtectedRegion(
                    region_id="region_1",
                    subject_refs=("capability_pay",),
                    protection_kind=ProtectionKind.IMMUTABLE,
                ),
            ),
        )
    )
    authorized_gate = SemanticEvolutionGate(
        identity_index=IdentityIndex,
        protection=EvolutionProtectionEvaluator(authority=authority),
        ledger=base.ledger,
    )
    verdict = authorized_gate.evaluate_candidate(
        parent, rewritten, delta, 7, authorization=authorization
    )
    assert verdict.feasible is True
    assert SELF_GOVERNANCE_REF in verdict.protection.regions_evaluated
    blocked = authorized_gate.evaluate_candidate(parent, rewritten, delta, 7)
    assert blocked.feasible is False
    assert blocked.protection.kind is ProtectionKind.CONSTITUTIONAL
    assert any("self-governance" in note for note in blocked.protection.notes)
    assert any("subject_refs reduced" in note for note in blocked.protection.notes)

    harness = UniversalEvolutionHarness()
    changed_parent = parent.with_system(
        dataclasses.replace(
            parent.system,
            protected_regions=(
                ProtectedRegion(
                    region_id="region_1",
                    subject_refs=(
                        "capability_pay", "rr1", "dep1", "t1.deadline", "w1",
                        "m1", "doc1", "req.pay", "crit.pay",
                    ),
                    protection_kind=ProtectionKind.IMMUTABLE,
                ),
            ),
        )
    )
    result = harness.loop.run(changed_parent, 3, 4, 7)
    assert result.generations_run == 0
    assert result.reconstructable is True
    assert harness.ledger.recorded_deltas() == ()


# =============================================================================
# 8.  E/H ownership intact across the search
# =============================================================================

def test_EH_ownership_intact(harness):
    """The boundary and testing-anchor carriers are byte-identical in the
    final selected ISR — the search's mutable surface is exactly the
    declared nine domains, never the E/H carriers."""
    result = harness.run(seed=7, generations=3, population_size=4)
    final = harness.replay(harness.parent_isr(), harness.ledger.recorded_deltas())
    before = IdentityIndex.derive(harness.parent_isr()).gene_hashes
    after = IdentityIndex.derive(final).gene_hashes
    assert before[("boundary", "b1")] == after[("boundary", "b1")]
    assert before[("testing_anchor", "anchor1")] == after[("testing_anchor", "anchor1")]
    assert result.generations_run == 3


# =============================================================================
# 9.  R2.8 is the only trust boundary
# =============================================================================

def test_r28_only_trust_boundary(harness):
    """The protection projection is consumed by the R2.8 gate stack; the
    universal-search module is inside that scan and carries no evaluation
    identifiers structurally, nor does it import observation machinery."""
    assert is_projection_consumed_by_r28() is True
    result = harness.run(seed=7, generations=3, population_size=4)
    assert result.reconstructable is True

    source = pathlib.Path(inspect.getfile(UniversalEvolutionLoop)).read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)
    banned = {"fitness", "score", "metric", "measurement"}
    names = {
        node.id for node in ast.walk(tree)
        if isinstance(node, ast.Name) and node.id in banned
    }
    attrs = {
        node.attr for node in ast.walk(tree)
        if isinstance(node, ast.Attribute) and node.attr in banned
    }
    assert names == set()
    assert attrs == set()
    assert "diversity" not in source
    assert "evolution_state" not in source


# =============================================================================
# 10.  Candidate identity is deterministic
# =============================================================================

def test_candidate_identity_deterministic():
    """Same seed -> same population -> same winners -> identical lineage
    and identical recorded delta content (the reproducibility the ledger
    replay depends on)."""
    first = UniversalEvolutionHarness()
    second = UniversalEvolutionHarness()
    r1 = first.run(seed=11, generations=3, population_size=4)
    r2 = second.run(seed=11, generations=3, population_size=4)
    assert r1.final_isr_semantic_hash == r2.final_isr_semantic_hash
    assert r1.generations_run == r2.generations_run
    assert r1.lineage == r2.lineage
    assert first.ledger.recorded_deltas() == second.ledger.recorded_deltas()


# =============================================================================
# 11.  Competing candidates compare deterministically
# =============================================================================

def test_competing_candidates_comparable_deterministically(harness):
    """The selection profile is a TUPLE (never a scalar): per-objective
    engagement bits in tier order, compared lexicographically, ties broken
    by delta_id. Re-selecting the same population yields the same winner,
    and the winner is the max under that order."""
    parent = harness.parent_isr()
    population = harness.variation.generate(parent, population_size=5, seed=3)
    pairs = [
        (apply_multi_gene_delta(parent, delta, 0), delta)
        for delta in population
    ]
    winner = harness.selector.select(pairs, parent)
    again = harness.selector.select(pairs, parent)
    assert winner[1] is again[1]

    objectives = {o.objective_id: o for o in parent.system.evolution_objectives}
    tiers = lexicographic_tiers(parent)

    def profile(delta):
        edited = {gene_id for _, gene_id in delta.edited_genes}
        return tuple(
            1 if set(objectives[tier].subject_refs) & edited else 0
            for tier in tiers
        )

    winner_profile = profile(winner[1])
    assert isinstance(winner_profile, tuple)
    for _, delta in pairs:
        assert winner_profile >= profile(delta)
    tied = {
        delta.delta_id
        for _, delta in pairs
        if profile(delta) == winner_profile
    }
    assert winner[1].delta_id == max(tied)


# =============================================================================
# 12.  The identity index is a derived projection
# =============================================================================

def test_identity_index_derived_not_mutatable(harness):
    """The R2.10.5 invariant: the index is a frozen dataclass with no
    mutation surface and derive-only construction; replacement is the
    module-level function producing a new ISR version with exactly one
    gene changed."""
    assert dataclasses.is_dataclass(IdentityIndex)
    assert IdentityIndex.__dataclass_params__.frozen
    mutators = {
        name for name in dir(IdentityIndex)
        if name.startswith(("add_", "remove_", "replace_", "set_"))
    }
    assert mutators == set()

    parent = harness.parent_isr()
    assert IdentityIndex.derive(parent) == IdentityIndex.derive(parent)
    index = IdentityIndex.derive(parent)
    assert index.genes
    assert index.path_identities

    capability = parent.system.business_capabilities[0]
    new_gene = dataclasses.replace(
        capability, intent="process a payment with dispute resolution"
    )
    next_isr = identity_index_replace_gene(
        index, parent, "capability", "capability_pay", new_gene
    )
    before = IdentityIndex.derive(parent).gene_hashes
    after = IdentityIndex.derive(next_isr).gene_hashes
    moved = {key for key in before if before[key] != after.get(key)}
    assert moved == {("capability", "capability_pay")}
    assert stable_isr_hash(next_isr) != stable_isr_hash(parent)


# =============================================================================
# 13.  Diversity observed over universal genes (observe-only)
# =============================================================================

def test_diversity_observation_over_universal_genes(harness):
    """Universal populations carry healthy genotype diversity, observable
    through the R2.9 observer — and observation NEVER perturbs the search
    (the loop holds no observer: identical seeds give identical results)."""
    parent = harness.parent_isr()
    population = harness.variation.generate(parent, population_size=6, seed=5)
    members = [
        PopulationMember(apply_multi_gene_delta(parent, delta, 0), "universal", delta)
        for delta in population
    ]
    metrics = DiversityObserver().observe_genotype(members)
    assert metrics.population_size == 6
    assert metrics.unique_isr_count >= 3
    assert metrics.genotype_entropy > 0.0

    result = harness.run(seed=5, generations=2, population_size=6)
    untouched = UniversalEvolutionHarness().run(
        seed=5, generations=2, population_size=6
    )
    assert result.final_isr_semantic_hash == untouched.final_isr_semantic_hash
    assert result.lineage == untouched.lineage


# =============================================================================
# 14.  All-infeasible halts honestly
# =============================================================================

def test_all_infeasible_halts_honestly():
    """A parent whose IMMUTABLE region covers every mutable-domain gene
    yields zero feasible candidates: the run halts at generation 0 with
    generations_run == 0, an empty lineage, a reconstructable True
    (initial == final), and nothing recorded."""
    harness = UniversalEvolutionHarness()
    parent = harness.parent_isr()
    locked = parent.with_system(
        dataclasses.replace(
            parent.system,
            protected_regions=(
                ProtectedRegion(
                    region_id="region_all",
                    subject_refs=(
                        "capability_pay", "rr1", "dep1", "t1.deadline", "w1",
                        "m1", "doc1", "req.pay", "crit.pay",
                    ),
                    protection_kind=ProtectionKind.IMMUTABLE,
                ),
            ),
            evolution_policies=(
                EvolutionPolicy(
                    policy_id="policy1",
                    objective_refs=("opt1",),
                    protected_region_refs=("region_all",),
                ),
            ),
        )
    )
    result = harness.loop.run(locked, 3, 4, 7)
    assert result.generations_run == 0
    assert result.lineage == ()
    assert result.reconstructable is True
    assert result.final_isr_semantic_hash == stable_isr_hash(locked)
    assert harness.ledger.recorded_deltas() == ()


# =============================================================================
# 15.  Option A — the twelfth use: no new carriers, no matrix movement
# =============================================================================

def test_option_a_holds_under_universal_search(harness):
    """R2.10.5 adds no carriers and moves no matrix row: the recipe ISR is
    byte-identical (the twelfth Option A use), the matrix stays 12/18/0/0,
    and the search leaves the J carriers' cardinality untouched."""
    assert RECIPE.content_hash == (
        "317b62a84dc1c4c0ee4a0e43c732a8d2d8b2f7b3c6b0404712a0fc5d6bb74613"
    )
    from tiannara.application.evolution.isr_capability_audit import (
        CapabilityStatus,
        ISRCapabilityAudit,
    )

    result = ISRCapabilityAudit().run(RECIPE)
    assert result.integrity is True
    assert result.isr_hash == RECIPE.content_hash
    summary = result.summary()
    assert (summary["expressed"], summary["partial"], summary["missing"]) == (
        12, 18, 0,
    )
    by_id = {c.capability_id: c.status for c in result.capabilities}
    assert CapabilityStatus.PROJECTED not in by_id.values()

    run_result = harness.run(seed=7, generations=3, population_size=4)
    final = harness.replay(
        harness.parent_isr(), harness.ledger.recorded_deltas()
    )
    assert len(final.system.evolution_objectives) == 1
    assert len(final.system.protected_regions) == 1
    assert len(final.system.evolution_policies) == 1
    assert run_result.reconstructable is True