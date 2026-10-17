"""plan_builder — deterministic intent → reqgraph → genome → ISR → plan.

Wires v1.2 (genesis), v1.3 (genome construction + materialization), and v1.4
(lowering) into the single entry point Campaign A uses.  No RNG on the seed
path: same workload ⇒ same plan + same candidate revision, always.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from compiler.core.lowering import isr_to_plan
from compiler.core.plan import CompilationPlan
from evolution.core.construction import ReferenceGenomeConstructor
from evolution.core.genome import Genome, genome_content_hash
from evolution.core.materialize import ReferenceGenomeMaterializer
from genesis.mapper import (
    CONSTITUTIONAL_DEFAULTS,
    ReferenceDeterministicMapper,
    constitutional_service_responsibility,
)
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


def _canon(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class PlanArtifacts:
    plan: CompilationPlan
    revision: ISRRevision
    genome: Genome
    requirement_graph: RequirementGraph
    requirement_graph_hash: str
    genome_hash: str
    plan_hash: str

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


_VERIFICATION_METHODS = {
    RequirementKind.FUNCTIONAL: "integration_test",
    RequirementKind.DOMAIN_CONCEPT: "domain_semantic_review",
    RequirementKind.CONSTRAINT: "constraint_policy_check",
    RequirementKind.NON_FUNCTIONAL: "observability_probe",
    RequirementKind.STAKEHOLDER: "stakeholder_acceptance_review",
}


def _architecture_declarations(w: Workload) -> dict[str, dict[str, list[dict]]]:
    """Deterministic explicit ISR architecture declarations for a workload.

    The corpus pipeline derives services, data models, events and the security
    policy from the genome. Everything the source-bound mapping contract
    requires beyond that derivation — typed capabilities for the domain,
    constraint, non-functional and stakeholder requirements; the API surface;
    frontend routes and interactions; effects, consequences and the category
    invariant; and the single canonical frontend/API/backend contract payload —
    is declared here as typed ``isr_nodes``/``isr_edges`` requirement
    properties. The genesis mapper projects declarations only after validating
    them against the ISR type system (see genesis/mapper.py), so this is a
    declaration surface, not an inference mechanism: nothing in this function
    reads candidate output, and the same workload always yields the same graph.
    """
    seeds = sorted(w.seeds)
    api_contract_id = "app"
    policy_id = "sec:policy"
    by_requirement: dict[str, dict[str, list[dict]]] = {}

    def attach(req_id: str, *, node: dict | None = None, edge: dict | None = None) -> None:
        bucket = by_requirement.setdefault(req_id, {"isr_nodes": [], "isr_edges": []})
        if node is not None:
            bucket["isr_nodes"].append(node)
        if edge is not None:
            bucket["isr_edges"].append(edge)

    def isr_node(node_id: str, node_type: str, req_id: str, properties: dict) -> dict:
        return {
            "id": node_id,
            "type": node_type,
            "properties": {**properties, "source_requirement_ids": [req_id]},
        }

    def isr_edge(edge_id: str, edge_type: str, source_id: str, target_id: str, req_id: str) -> dict:
        return {
            "id": edge_id,
            "type": edge_type,
            "source_id": source_id,
            "target_id": target_id,
            "properties": {"source_requirement_ids": [req_id]},
        }

    operations: list[dict] = []
    for seed in seeds:
        operations.append({
            "operation_id": f"get_{seed}", "method": "GET", "path": f"/{seed}",
            "request_schema": None, "response_schema": None,
            "authorization_policy": policy_id, "errors": [],
            "idempotency_required": False, "paginated": False, "version": "v1",
        })
        operations.append({
            "operation_id": f"create_{seed}", "method": "POST", "path": f"/{seed}",
            "request_schema": None, "response_schema": None,
            "authorization_policy": policy_id, "errors": [],
            "idempotency_required": True, "paginated": False, "version": "v1",
        })

    frontend_contract = {
        "schema_version": "1", "contract_id": "frontend:app",
        "routes": [f"/{seed}" for seed in seeds],
        "api_contract_id": api_contract_id,
        "quality_obligation_ids": [],
        "state_domains": list(seeds),
        "interaction_flows": [f"manage-{seed}" for seed in seeds],
        "accessibility_requirements": ["keyboard-navigation"],
        "observability_requirements": ["latency-budget"],
        "modules": [
            {
                "module_id": f"{seed}-page",
                "responsibility": f"Manage {seed}",
                "dependencies": [],
                "invariants": [f"{seed}-name-non-empty"],
            }
            for seed in seeds
        ],
        "data_flows": [
            {
                "flow_id": f"manage-{seed}",
                "source": f"{seed}-page",
                "destination": f"POST /{seed}",
                "contract": f"{seed}-record",
                "failure_policy": "show-error",
            }
            for seed in seeds
        ],
        "security_boundaries": [policy_id],
        "failure_states": [f"manage-{seed}-failed" for seed in seeds],
        "design_constraints": ["responsive"],
    }

    backend_modules = [
        {
            "module_id": f"service:dom:{seed}",
            "responsibility": f"{seed} as a first-class concept",
            "dependencies": [],
            "invariants": [f"{seed}-name-non-empty"],
        }
        for seed in seeds
    ] + [
        {
            "module_id": f"service:constitution:{default}",
            "responsibility": constitutional_service_responsibility(default),
            "dependencies": [],
            "invariants": [f"{default}-baseline-holds"],
        }
        for default in CONSTITUTIONAL_DEFAULTS
    ]
    backend_contract = {
        "schema_version": "1", "contract_id": "backend:app",
        "domain_modules": list(seeds),
        "api_contract_id": api_contract_id,
        "quality_obligation_ids": [],
        "persistence_targets": [f"dm:dom:{seed}" for seed in seeds],
        "event_targets": ["event:domain"],
        "observability_requirements": ["health"],
        "modules": backend_modules,
        "data_flows": [
            {
                "flow_id": f"manage-{seed}",
                "source": f"create_{seed}",
                "destination": f"dm:dom:{seed}",
                "contract": f"{seed}-record",
                "failure_policy": "rollback",
            }
            for seed in seeds
        ],
        "security_boundaries": [policy_id],
        "failure_modes": ["store-unavailable", "idempotency-conflict"],
    }

    # Domain requirements: persisted concept, typed capability chain, and the
    # service node (with the single backend contract payload on the carrier).
    for seed in seeds:
        dom_req = f"dom:{seed}"
        service_properties = {
            "style": "bounded-context",
            "responsibility": f"{seed} as a first-class concept",
            "source_requirement_ref": f"requirement_ref:{dom_req}",
        }
        if seed == seeds[0]:
            service_properties["backend_contract"] = backend_contract
        attach(dom_req, node=isr_node(
            f"service:dom:{seed}", "service", dom_req, service_properties,
        ))
        attach(dom_req, node=isr_node(
            f"dm:dom:{seed}", "data_model", dom_req,
            {
                "storage": "json",
                "fields": [
                    {"name": f"{seed}_id", "type": "string", "required": True, "unique": True},
                ],
                "invariants": [f"{seed}_id is unique"],
            },
        ))
        attach(dom_req, edge=isr_edge(
            f"satisfies:{dom_req}", "satisfies",
            f"capability:fn:{seed}", f"requirement_ref:{dom_req}", dom_req,
        ))

    # Stakeholder requirement: operational oversight implemented by the
    # observability constitution service.
    attach("stake:operator", node=isr_node(
        "capability:stake:operator", "capability", "stake:operator",
        {
            "name": "Operate the generated system",
            "description": "Operational oversight of the generated system",
        },
    ))
    attach("stake:operator", edge=isr_edge(
        "satisfies:stake:operator", "satisfies",
        "capability:stake:operator", "requirement_ref:stake:operator", "stake:operator",
    ))
    attach("stake:operator", edge=isr_edge(
        "implemented-by:stake:operator", "implemented_by",
        "capability:stake:operator", "service:constitution:observability", "stake:operator",
    ))

    # Category constraint: implemented by the security constitution service and
    # carried as the first-class invariant every effect must uphold.
    attach("con:category", node=isr_node(
        "capability:con:category", "capability", "con:category",
        {"name": "Category constraint", "description": CATEGORY_CONSTRAINTS[w.category]},
    ))
    attach("con:category", edge=isr_edge(
        "satisfies:con:category", "satisfies",
        "capability:con:category", "requirement_ref:con:category", "con:category",
    ))
    attach("con:category", edge=isr_edge(
        "implemented-by:con:category", "implemented_by",
        "capability:con:category", "service:constitution:security", "con:category",
    ))
    attach("con:category", node=isr_node(
        "invariant:category", "invariant", "con:category",
        {
            "expression": CATEGORY_CONSTRAINTS[w.category],
            "enforcement_point": "runtime",
            "verification_method": "integration_test",
        },
    ))
    # The cross-domain event channel derived from the messaging chromosome
    # (event-driven with >= 2 domains) carries explicit delivery semantics.
    attach("con:category", node=isr_node(
        "event:domain", "event", "con:category",
        {
            "delivery_guarantee": "at-least-once",
            "ordering": "per-aggregate",
            "payload_schema": "domain-event/1",
        },
    ))

    # Non-functional baseline: implemented by the observability constitution
    # service; carries the single API node and canonical API contract payload.
    attach("nf:baseline", node=isr_node(
        "capability:nf:baseline", "capability", "nf:baseline",
        {
            "name": "Bounded, observable operation",
            "description": "bounded latency and observable operations",
        },
    ))
    attach("nf:baseline", edge=isr_edge(
        "satisfies:nf:baseline", "satisfies",
        "capability:nf:baseline", "requirement_ref:nf:baseline", "nf:baseline",
    ))
    attach("nf:baseline", edge=isr_edge(
        "implemented-by:nf:baseline", "implemented_by",
        "capability:nf:baseline", "service:constitution:observability", "nf:baseline",
    ))
    attach("nf:baseline", node=isr_node(
        "api:app", "api", "nf:baseline",
        {
            "operations": operations,
            "global_error_contract": {"schema": "ProblemDetails"},
            "auth_scheme": "bearer",
            "api_contract": {
                "schema_version": "1",
                "contract_id": api_contract_id,
                "operations": operations,
                "global_error_contract": "problem-json",
                "auth_scheme": "bearer",
                "schemas": [],
            },
        },
    ))

    # Functional requirements: route, interaction, effect and consequence per
    # seed; the first route carries the single frontend contract payload.
    for seed in seeds:
        fn_req = f"fn:{seed}"
        route_properties: dict = {"path": f"/{seed}"}
        if seed == seeds[0]:
            route_properties["frontend_contract"] = frontend_contract
        attach(fn_req, node=isr_node(
            f"ui:route:{seed}", "frontend_route", fn_req, route_properties,
        ))
        attach(fn_req, node=isr_node(
            f"ui:interaction:manage-{seed}", "frontend_interaction", fn_req,
            {"action": f"manage_{seed}", "flow_id": f"manage-{seed}"},
        ))
        attach(fn_req, node=isr_node(
            f"effect:manage-{seed}", "effect", fn_req,
            {
                "effect_type": "create",
                "idempotency_policy": "required",
                "replay_policy": "deduplicate",
                "failure_policy": "rollback",
                "effect_path": {
                    "operation_id": f"create_{seed}",
                    "frontend_flow_id": f"manage-{seed}",
                    "domain_module": seed,
                    "effect_id": f"effect:manage-{seed}",
                    "authorization_boundary": policy_id,
                    "consequence": f"consequence:manage-{seed}",
                },
            },
        ))
        attach(fn_req, node=isr_node(
            f"consequence:manage-{seed}", "consequence", fn_req,
            {
                "trigger": f"duplicate or repeated manage request for {seed}",
                "outcome": "return prior result",
                "failure_policy": "no duplicate side effect",
                "effect_consequence": {
                    "effect_id": f"effect:manage-{seed}",
                    "persistence": f"dm:dom:{seed}",
                    "event": "event:domain",
                    "idempotency_key": "request-id",
                    "uniqueness_constraint": f"{seed}-id",
                    "retry_policy": "bounded",
                    "concurrency_policy": "optimistic-lock",
                    "recovery_policy": "return-prior-result",
                },
            },
        ))
        attach(fn_req, edge=isr_edge(
            f"routes-to:{seed}", "routes_to", f"ui:route:{seed}", "api:app", fn_req,
        ))
        attach(fn_req, edge=isr_edge(
            f"invokes:manage-{seed}", "invokes",
            f"ui:interaction:manage-{seed}", "api:app", fn_req,
        ))
        attach(fn_req, edge=isr_edge(
            f"causes-effect:{seed}", "causes_effect",
            "api:app", f"effect:manage-{seed}", fn_req,
        ))
        attach(fn_req, edge=isr_edge(
            f"requires-invariant:{seed}", "requires_invariant",
            f"effect:manage-{seed}", "invariant:category", fn_req,
        ))
        attach(fn_req, edge=isr_edge(
            f"consequence-of:{seed}", "consequence_of",
            f"consequence:manage-{seed}", f"effect:manage-{seed}", fn_req,
        ))

    return by_requirement


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

    declarations = _architecture_declarations(w)
    for req_id, node in list(nodes.items()):
        extra: dict = {"verification_method": _VERIFICATION_METHODS[node.kind]}
        bucket = declarations.get(req_id)
        if bucket:
            extra.update(bucket)
        nodes[req_id] = node.model_copy(
            update={"properties": {**node.properties, **extra}}
        )

    return RequirementGraph(schema_version="1.0", nodes=nodes, edges=edges)


def build_artifacts_for(w: Workload) -> PlanArtifacts:
    return build_artifacts_from_graph(intent_to_requirement_graph(w), w)


def build_artifacts_from_graph(rg: RequirementGraph, w: Workload) -> PlanArtifacts:
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
    gh = genome_content_hash(genome)
    candidate_graph = ReferenceGenomeMaterializer().materialize(genome)
    cand = ISRRevision.create(
        system_id=system, revision_id=f"rev1:{gh[:16]}",
        schema_version="1.0", graph=candidate_graph,
        provenance=Provenance(parent_revision_id=rev0.revision_id,
                              derivation_refs=[f"construct:{gh[:16]}"],
                              created_by="evolution_engine", created_at=FIXED_TS))

    plan = isr_to_plan(cand)
    rg_hash = _sha(_canon(rg.model_dump()))
    plan_hash = _sha(_canon(plan.model_dump()))

    return PlanArtifacts(
        plan=plan, revision=cand, genome=genome, requirement_graph=rg,
        requirement_graph_hash=rg_hash, genome_hash=gh, plan_hash=plan_hash,
    )


def build_plan_for(w: Workload) -> tuple[CompilationPlan, ISRRevision, str, str]:
    """Backward-compatible wrapper.  Returns (plan, revision, rg_hash, genome_hash)."""
    a = build_artifacts_for(w)
    return a.plan, a.revision, a.requirement_graph_hash, a.genome_hash
