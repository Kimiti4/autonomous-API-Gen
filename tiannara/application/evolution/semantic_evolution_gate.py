"""R2.10.4 — SemanticEvolutionGate: universal ISR evolution integration.

R2.10.1 (A) proved per-gene identity; R2.10.2 (B-H) and R2.10.3 (I, J)
added the semantic primitives. R2.10.4 proves they COMPOSE: one candidate
evolves at least four independent genes across distinct domains while
locality, cross-gene reference integrity, the E/H/J protection authority,
the R2.8 evidence substrate, backend independence, and reproducibility /
ledger verifiability all hold — and negative variants must fail visibly.

The gate contract:

  1. FEASIBILITY FIRST — the J protection projection (resolved from the
     PARENT constitution) runs before any proof and before any objective
     evaluation. An infeasible candidate is returned immediately, with no
     proofs and no ledger event.
  2. ≥4 independent genes across ≥4 distinct domains — a single-gene
     evolution is not a composition and cannot be substituted for it
     (no single-gene fallback).
  3. Four proofs, all of which must hold:
       locality             — exactly the declared genes moved, nothing else
                              disturbed (identity-index hashes, one
                              namespace).
       reference_integrity  — the candidate introduces no new dangling
                              cross-gene reference.
       backend_independence — all ten primitives' mechanism lints hold on
                              the candidate (8 named lints + capability
                              free-text scan + temporal by-construction).
       r28_evidence_path    — the gate holds no evaluation machinery of its
                              own: the protection projection is consumed by
                              the R2.8 gate stack (AST scan of the
                              evolution-gate sources).
  4. Every feasible evaluation is recorded in the ledger (MEASUREMENT
     event, chain-anchored) with the canonical edit list, seed, proof
     outcomes, and before/after hashes — reproducible and verifiable.

Parent-authoritative invariant (permanent, enforced two ways): a candidate
is judged by the rules it was generated under, never by rules it authored.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from constitutional_architecture.isr.semantics.boundary import (
    BOUNDARY_MECHANISM_TERMS,
    assert_boundary_technology_agnostic,
)
from constitutional_architecture.isr.semantics.deployment import (
    DEPLOYMENT_MECHANISM_TERMS,
    assert_deployment_technology_agnostic,
)
from constitutional_architecture.isr.semantics.documentation import (
    DOCUMENTATION_MECHANISM_TERMS,
    assert_documentation_technology_agnostic,
)
from constitutional_architecture.isr.semantics.evolution_policy import (
    EVOLUTION_MECHANISM_TERMS,
    EvolutionPolicy,
    assert_evolution_technology_agnostic,
)
from constitutional_architecture.isr.semantics.migration import (
    MIGRATION_MECHANISM_TERMS,
    assert_migration_technology_agnostic,
)
from constitutional_architecture.isr.semantics.reliability import (
    RELIABILITY_MECHANISM_TERMS,
    assert_reliability_technology_agnostic,
)
from constitutional_architecture.isr.semantics.requirement import (
    REQUIREMENT_MECHANISM_TERMS,
    assert_requirement_technology_agnostic,
)
from constitutional_architecture.isr.semantics.testing_anchor import (
    TESTING_MECHANISM_TERMS,
    assert_testing_technology_agnostic,
)

from .identity_index import SemanticIdentityIndex
from .ledger import EventType, EvolutionEvent, stable_isr_hash
from .protection import EvolutionProtectionEvaluator, ProtectionResult


# -- composition vocabulary ----------------------------------------------------

@dataclass(frozen=True)
class GeneEdit:
    """One declared gene replacement: (domain, gene_id) -> new gene."""

    domain: str
    gene_id: str
    new_gene: Any


@dataclass(frozen=True)
class MultiGeneDelta:
    """A composition: ≥4 independent gene edits across distinct domains."""

    delta_id: str
    edits: tuple[GeneEdit, ...]

    @property
    def edited_domains(self) -> frozenset[str]:
        return frozenset(edit.domain for edit in self.edits)

    @property
    def edited_genes(self) -> frozenset[tuple[str, str]]:
        return frozenset((edit.domain, edit.gene_id) for edit in self.edits)


@dataclass(frozen=True)
class GateProof:
    """One proof with its verdict and evidence. Negative variants must
    produce held=False with evidence naming exactly what failed."""

    proof_id: str
    held: bool
    evidence: str


@dataclass(frozen=True)
class SemanticEvolutionVerdict:
    """The composition verdict.

    ``feasible`` is True only if protection passed AND every proof held.
    ``policy_resolved_from`` is always "parent" — the invariant, verified
    by construction (see evaluate).
    ``ledger_event_range`` is the (start, end) event-hash range the gate
    recorded when feasible (None when infeasible or no ledger attached).
    """

    feasible: bool
    candidate_semantic_hash: str
    protection: ProtectionResult
    proofs: tuple[GateProof, ...]
    policy_resolved_from: str = "parent"
    ledger_event_range: Optional[tuple[str, str]] = None


PROOF_LOCALITY = "locality"
PROOF_REFERENCE_INTEGRITY = "reference_integrity"
PROOF_BACKEND_INDEPENDENCE = "backend_independence"
PROOF_R28_EVIDENCE_PATH = "r28_evidence_path"


# -- policy resolution ---------------------------------------------------------

def resolve_evolution_policy(isr: Any) -> EvolutionPolicy:
    """THE parent-authoritative policy resolution: the rules a candidate is
    judged under always come from the PARENT constitution.

    Single policy -> that policy. Multiple policies -> deterministic merge
    (union of refs, first-occurrence order). No policy -> a default policy
    that governs nothing (protection vacuously passes).
    """
    policies = tuple(isr.system.evolution_policies)
    if not policies:
        return EvolutionPolicy(policy_id="parent")
    if len(policies) == 1:
        return policies[0]

    def merged(field: str) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                ref for policy in policies for ref in getattr(policy, field)
            )
        )

    return EvolutionPolicy(
        policy_id="merged",
        objective_refs=merged("objective_refs"),
        protected_region_refs=merged("protected_region_refs"),
        selection_constraints=merged("selection_constraints"),
    )


# -- deterministic multi-gene application --------------------------------------

def apply_multi_gene_delta(isr: Any, delta: MultiGeneDelta, seed: int = 0):
    """Apply a delta deterministically: edits in canonical order sorted by
    (domain, gene_id). The delta IS the content — ``seed`` is accepted for
    the harness protocol and reserved for future stochastic sub-strategies,
    never used for ordering.

    Unknown genes raise KeyError (rejection before evaluation). Replacement
    is mechanical; the gate evaluates the candidate and its proofs after.
    """
    del seed
    index = SemanticIdentityIndex()
    current = isr
    for edit in sorted(delta.edits, key=lambda e: (e.domain, e.gene_id)):
        current = index.replace_gene(current, edit.domain, edit.gene_id, edit.new_gene)
    return current


# -- r28 evidence path (the gate holds no evaluator of its own) ----------------

def _module_free_of_evaluation_machinery(source: Path) -> bool:
    tree = ast.parse(source.read_text(encoding="utf-8"))
    banned = {"fitness", "score", "metric", "measurement"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in banned:
            return False
        if isinstance(node, ast.Attribute) and node.attr in banned:
            return False
    return True


def is_projection_consumed_by_r28() -> bool:
    """The protection projection is consumed by the R2.8 gate stack: neither
    the gate nor the protection module may contain evaluation machinery
    (fitness / score / metric / measurement identifiers, structurally)."""
    here = Path(__file__)
    return _module_free_of_evaluation_machinery(
        here
    ) and _module_free_of_evaluation_machinery(here.parent / "protection.py")


# -- the gate ------------------------------------------------------------------

class SemanticEvolutionGate:
    """Compose ≥4 independent gene evolutions under the constitutional gate.

    Designed to SURFACE composition failures: positive evolutions hold all
    four proofs; negative variants (hidden side effects, dangling refs,
    technology coupling) fail visibly with proof evidence naming the exact
    disturbance.
    """

    def __init__(
        self,
        identity_index: Any = None,
        protection: Any = None,
        ledger: Any = None,
    ) -> None:
        self._identity_index = identity_index or SemanticIdentityIndex()
        self._protection = protection or EvolutionProtectionEvaluator()
        self._ledger = ledger

    # -- the composition evaluation ---------------------------------------------

    def evaluate(self, parent_isr: Any, delta: MultiGeneDelta, seed: int = 0):
        """Apply the delta and evaluate the composition."""
        self._require_composition(delta)
        candidate = self._apply(parent_isr, delta, seed)
        return self.evaluate_candidate(parent_isr, candidate, delta, seed)

    def evaluate_candidate(
        self, parent_isr: Any, candidate: Any, delta: MultiGeneDelta, seed: int = 0
    ) -> SemanticEvolutionVerdict:
        """Evaluate an externally-built candidate against the parent (the
        application-layer failure-injection seam: a caller that applied the
        delta wrongly still gets judged by the gate)."""
        policy = resolve_evolution_policy(parent_isr)
        protection = self._protection.evaluate(parent_isr, candidate, policy)
        if not protection.protected_ok:
            # FEASIBILITY FIRST: no proof, no objective evaluation, no
            # ledger event for an infeasible candidate.
            return SemanticEvolutionVerdict(
                False,
                stable_isr_hash(candidate),
                protection,
                (),
                "parent",
                None,
            )
        proofs = (
            self._prove_locality(parent_isr, candidate, delta),
            self._prove_reference_integrity(parent_isr, candidate),
            self._prove_backend_independence(candidate),
            self._prove_r28_evidence_path(),
        )
        feasible = all(proof.held for proof in proofs)
        ledger_range = (
            self._record(parent_isr, candidate, delta, seed, proofs)
            if feasible and self._ledger is not None
            else None
        )
        return SemanticEvolutionVerdict(
            feasible,
            stable_isr_hash(candidate),
            protection,
            proofs,
            "parent",
            ledger_range,
        )

    # -- the application seam (harnesses may inject application-layer bugs) -------

    def _apply(self, parent_isr: Any, delta: MultiGeneDelta, seed: int):
        return apply_multi_gene_delta(parent_isr, delta, seed)

    def _require_composition(self, delta: MultiGeneDelta) -> None:
        if len(delta.edits) < 4:
            raise ValueError(
                "a composition needs >= 4 independent gene edits "
                f"(got {len(delta.edits)})"
            )
        if len(delta.edited_domains) < 4:
            raise ValueError(
                "a composition needs >= 4 distinct domains "
                f"(got {sorted(delta.edited_domains)})"
            )

    # -- the four proofs ---------------------------------------------------------

    def _prove_locality(
        self, parent_isr: Any, candidate: Any, delta: MultiGeneDelta
    ) -> GateProof:
        before = self._identity_index.gene_hashes(parent_isr)
        after = self._identity_index.gene_hashes(candidate)
        edited = delta.edited_genes
        disturbed = sorted(
            (domain, gene_id)
            for (domain, gene_id), after_hash in after.items()
            if before.get((domain, gene_id)) != after_hash
            and (domain, gene_id) not in edited
        )
        held = not disturbed
        evidence = (
            f"moved {len(edited)} declared gene(s), 0 disturbed"
            if held
            else f"moved {len(edited)} declared gene(s) but disturbed "
                 f"{len(disturbed)} undeclared gene(s): {disturbed}"
        )
        return GateProof(PROOF_LOCALITY, held, evidence)

    def _prove_reference_integrity(
        self, parent_isr: Any, candidate: Any
    ) -> GateProof:
        before = self._identity_index.dangling_references(parent_isr)
        after = self._identity_index.dangling_references(candidate)
        newly_dangling = tuple(d for d in after if d not in before)
        held = not newly_dangling
        evidence = (
            "no new dangling cross-gene reference"
            if held
            else f"new dangling cross-gene reference(s): {newly_dangling}"
        )
        return GateProof(PROOF_REFERENCE_INTEGRITY, held, evidence)

    def _prove_backend_independence(self, candidate: Any) -> GateProof:
        hits: list[str] = []
        system = candidate.system
        all_terms = (
            BOUNDARY_MECHANISM_TERMS
            | DEPLOYMENT_MECHANISM_TERMS
            | DOCUMENTATION_MECHANISM_TERMS
            | EVOLUTION_MECHANISM_TERMS
            | MIGRATION_MECHANISM_TERMS
            | RELIABILITY_MECHANISM_TERMS
            | REQUIREMENT_MECHANISM_TERMS
            | TESTING_MECHANISM_TERMS
        )
        for capability in system.business_capabilities:
            leaked = tuple(
                term for term in all_terms if term in capability.intent.lower()
            )
            if leaked:
                hits.append(
                    f"capability '{capability.capability_id}' intent couples "
                    f"to mechanism(s): {leaked}"
                )
        migration_carriers = tuple(
            migration
            for module in system.modules
            for migration in module.data_migrations
        )
        linted = (
            ("migration", migration_carriers, assert_migration_technology_agnostic),
            ("reliability", system.reliability_requirements,
             assert_reliability_technology_agnostic),
            ("boundary", system.architectural_boundaries,
             assert_boundary_technology_agnostic),
            ("deployment", system.deployment_intents,
             assert_deployment_technology_agnostic),
            ("requirement", system.requirements,
             assert_requirement_technology_agnostic),
            ("testing_anchor", system.testing_anchors,
             assert_testing_technology_agnostic),
            ("documentation", system.documentation_intents,
             assert_documentation_technology_agnostic),
            ("evolution", system.evolution_policies,
             assert_evolution_technology_agnostic),
        )
        for name, carriers, lint in linted:
            for gene in carriers:
                try:
                    lint(gene)
                except ValueError as exc:
                    hits.append(f"{name}: {exc}")
        held = not hits
        evidence = (
            "all 10 primitives' mechanism lints hold (8 named lints + "
            "capability free-text scan + temporal by-construction): "
            + ("clean" if held else f"coupling found: {hits}")
        )
        return GateProof(PROOF_BACKEND_INDEPENDENCE, held, evidence)

    def _prove_r28_evidence_path(self) -> GateProof:
        held = is_projection_consumed_by_r28()
        return GateProof(
            PROOF_R28_EVIDENCE_PATH,
            held,
            "protection projection consumed by the R2.8 gate stack; "
            "no evaluation machinery in evolution-gate sources"
            if held
            else "evaluation machinery found in evolution-gate sources",
        )

    # -- the ledger binding -------------------------------------------------------

    def _record(
        self,
        parent_isr: Any,
        candidate: Any,
        delta: MultiGeneDelta,
        seed: int,
        proofs: tuple[GateProof, ...],
    ) -> tuple[str, str]:
        event = EvolutionEvent(
            event_id=f"semantic-gate-{delta.delta_id}",
            evolution_id=delta.delta_id,
            sequence=0,
            event_type=EventType.MEASUREMENT,
            subject_id=delta.delta_id,
            payload={
                "seed": seed,
                "edits": [
                    {"domain": edit.domain, "gene_id": edit.gene_id}
                    for edit in sorted(delta.edits, key=lambda e: (e.domain, e.gene_id))
                ],
                "proofs": [
                    {"proof_id": proof.proof_id, "held": proof.held}
                    for proof in proofs
                ],
            },
            isr_hash=stable_isr_hash(parent_isr),
            candidate_hash=stable_isr_hash(candidate),
        )
        self._ledger.append_event(event, evolution_id=delta.delta_id)
        event_hash = self._ledger.latest_event_hash
        return (event_hash, event_hash)