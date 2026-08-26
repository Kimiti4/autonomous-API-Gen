"""plan_builder — deterministic intent → reqgraph → genome → ISR → plan.

Wires v1.2 (genesis), v1.3 (genome construction + materialization), and v1.4
(lowering) into the single entry point Campaign A uses.  No RNG on the seed
path: same workload ⇒ same plan + same candidate revision, always.
"""
from __future__ import annotations

from compiler.core.lowering import isr_to_plan
from compiler.core.plan import CompilationPlan
from evolution.core.construction import ReferenceGenomeConstructor
from evolution.core.genome import genome_content_hash
from evolution.core.materialize import ReferenceGenomeMaterializer
from genesis.mapper import ReferenceDeterministicMapper
from isr.core.identity import Provenance, compute_content_hash
from isr.core.revision import ISRRevision
from reqgraph.core.graph import (
    Priority, RequirementEdge, RequirementEdgeType, RequirementGraph,
    RequirementKind, RequirementNode,
)
from reqgraph.core.invariants import validate_requirement_graph

from ..corpus.corpus import Category, Workload

FIXED_TS = "2026-01-01T00:00:00Z"
MAPPING_SPEC = "map-1.0"

CATEGORY_CONSTRAINTS = {
    Category.CRUD_SAAS:   "tenant isolation between customer workspaces",
    Category.ERP:         "posted financial records are immutable",
    Category.BANKING:     "every balance change is an audited, idempotent ledger entry",
    Category.HEALTHCARE:  "clinical data access is least-privilege and audited",
    Category.LOGISTICS:   "shipment state transitions are replayable from events",
    Category.AI:          "model artefacts are versioned and reproducible",
    Category.GAMING:      "player state changes are authoritative and rate-limited",
    Category.IOT:         "telemetry ingest is bounded and back-pressured",
    Category.ROBOTICS:    "command streams fail safe on loss of heartbeat",
    Category.DISTRIBUTED: "coordination decisions carry explicit consistency bounds",
    Category.EMBEDDED:    "control loops execute within a bounded deadline",
    Category.API:         "client access is scoped by credential and quota",
    Category.STREAMING:   "per-stream processing guarantees are explicitly stated",
}


def _slug(s: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in s.lower()).strip("-")


def intent_to_requirement_graph(w: Workload) -> RequirementGraph:
    nodes: dict[str, RequirementNode] = {}
    edges: dict[str, RequirementEdge] = {}

    stake = "stake:operator"
    nodes[stake] = RequirementNode(
        id=stake, kind=RequirementKind.STAKEHOLDER,
        statement=f"operator of {w.intent}", priority=Priority.SHOULD,
        ambiguity_score=0.0, source_refs=[w.intent])

    seeds = sorted(w.seeds)
    for seed in seeds:
        dom, fn = f"dom:{seed}", f"fn:{seed}"
        nodes[dom] = RequirementNode(
            id=dom, kind=RequirementKind.DOMAIN_CONCEPT,
            statement=f"{seed} as a first-class concept", priority=Priority.MUST,
            ambiguity_score=0.0, source_refs=[w.intent])
        nodes[fn] = RequirementNode(
            id=fn, kind=RequirementKind.FUNCTIONAL,
            statement=f"manage {seed} for {w.intent}", priority=Priority.MUST,
            acceptance_criteria=[f"{seed} can be created and validated",
                                 f"{seed} can be queried by identifier"],
            ambiguity_score=0.1, source_refs=[w.intent])
        edges[f"ref:{fn}"] = RequirementEdge(
            id=f"ref:{fn}", type=RequirementEdgeType.REFINES, source_id=fn, target_id=dom)
        edges[f"own:{fn}"] = RequirementEdge(
            id=f"own:{fn}", type=RequirementEdgeType.OWNED_BY, source_id=fn, target_id=stake)

    fns = [f"fn:{s}" for s in seeds]
    for a, b in zip(fns, fns[1:]):
        edges[f"dep:{a}:{b}"] = RequirementEdge(
            id=f"dep:{a}:{b}", type=RequirementEdgeType.DEPENDS_ON, source_id=a, target_id=b)

    nodes["con:category"] = RequirementNode(
        id="con:category", kind=RequirementKind.CONSTRAINT,
        statement=CATEGORY_CONSTRAINTS[w.category], priority=Priority.MUST,
        ambiguity_score=0.0, source_refs=[w.category.value])
    nodes["nf:baseline"] = RequirementNode(
        id="nf:baseline", kind=RequirementKind.NON_FUNCTIONAL,
        statement="bounded latency and observable operations", priority=Priority.SHOULD,
        acceptance_criteria=["health and readiness are observable"],
        ambiguity_score=0.1, source_refs=[w.intent])

    return RequirementGraph(schema_version="1.0", nodes=nodes, edges=edges)


def build_plan_for(w: Workload) -> tuple[CompilationPlan, ISRRevision, str, str]:
    rg = intent_to_requirement_graph(w)
    validate_requirement_graph(rg)

    genesis = ReferenceDeterministicMapper().map(rg, MAPPING_SPEC)
    g0 = compute_content_hash("1.0", genesis.graph)
    system = _slug(w.intent)
    rev0 = ISRRevision.create(
        system_id=system, revision_id=f"rev0:{g0[:16]}", schema_version="1.0",
        graph=genesis.graph,
        provenance=Provenance(requirement_refs=sorted(rg.nodes),
                              derivation_refs=[f"genesis:{MAPPING_SPEC}"],
                              created_by="genesis", created_at=FIXED_TS))

    genome = ReferenceGenomeConstructor().construct(rev0)
    genome_hash = genome_content_hash(genome)
    candidate_graph = ReferenceGenomeMaterializer().materialize(genome)
    cand = ISRRevision.create(
        system_id=system, revision_id=f"rev1:{genome_hash[:16]}",
        schema_version="1.0", graph=candidate_graph,
        provenance=Provenance(parent_revision_id=rev0.revision_id,
                              derivation_refs=[f"construct:{genome_hash[:16]}"],
                              created_by="evolution_engine", created_at=FIXED_TS))

    return isr_to_plan(cand), cand, g0, genome_hash
