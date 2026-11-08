"""B-04 lowering obligation diff / deterministic re-lowering verifier (R1-W06)."""

from __future__ import annotations

from dataclasses import dataclass

from compiler.core.lowering import isr_to_plan
from compiler.core.plan import CompilationPlan
from compiler.core.plan_binding import compute_plan_digest
from isr.core.graph import EdgeType, NodeType
from isr.core.revision import ISRRevision

# Explicit loss per B-04 contract — must not appear on CompilationPlan carriers.
_LOSSY_EXPLICIT_NODE_TYPES: frozenset[NodeType] = frozenset(
    {
        NodeType.DOMAIN,
        NodeType.CAPABILITY,
        NodeType.REQUIREMENT_REF,
        NodeType.INFRASTRUCTURE_TARGET,
    }
)

_BEHAVIORAL_NODE_TYPES: frozenset[NodeType] = frozenset(
    {
        NodeType.SERVICE,
        NodeType.API,
        NodeType.DATA_MODEL,
        NodeType.EVENT,
        NodeType.SECURITY_POLICY,
        NodeType.EFFECT,
        NodeType.INVARIANT,
        NodeType.CONSEQUENCE,
        NodeType.FRONTEND_ROUTE,
        NodeType.FRONTEND_INTERACTION,
    }
)


@dataclass(frozen=True, slots=True)
class B04LoweringVerificationReport:
    passed: bool
    findings: tuple[str, ...]
    lossy_node_ids: tuple[str, ...]
    preserved_evidence: tuple[str, ...]


def _node_ids(graph, node_type: NodeType) -> frozenset[str]:
    return frozenset(
        nid for nid, node in graph.nodes.items() if node.type == node_type
    )


def verify_b04_lowering_obligations(
    revision: ISRRevision,
    plan: CompilationPlan,
) -> B04LoweringVerificationReport:
    """Compare ISR behavioral projection to lowered plan (not full plan→ISR rebuild)."""
    findings: list[str] = []
    evidence: list[str] = []
    graph = revision.graph

    expected_plan_id = f"plan:{revision.content_hash[:16]}"
    if plan.plan_id != expected_plan_id:
        findings.append(f"plan_id-mismatch:{plan.plan_id}!={expected_plan_id}")
    else:
        evidence.append("plan_id-bound-to-isr-hash")

    if plan.isr_id != revision.system_id:
        findings.append(f"isr_id-mismatch:{plan.isr_id}!={revision.system_id}")
    else:
        evidence.append("isr_id-match")

    checks: tuple[tuple[str, frozenset[str], frozenset[str]], ...] = (
        ("api", _node_ids(graph, NodeType.API), frozenset(a.id for a in plan.apis)),
        ("effect", _node_ids(graph, NodeType.EFFECT), frozenset(e.id for e in plan.effects)),
        (
            "security",
            _node_ids(graph, NodeType.SECURITY_POLICY),
            frozenset(s.policy_id for s in plan.security),
        ),
        ("invariant", _node_ids(graph, NodeType.INVARIANT), frozenset(i.id for i in plan.invariants)),
        (
            "consequence",
            _node_ids(graph, NodeType.CONSEQUENCE),
            frozenset(c.id for c in plan.consequences),
        ),
        ("service", _node_ids(graph, NodeType.SERVICE), frozenset(s.id for s in plan.services)),
        (
            "data_model",
            _node_ids(graph, NodeType.DATA_MODEL),
            frozenset(dm.id for dm in plan.data_models),
        ),
        ("event", _node_ids(graph, NodeType.EVENT), frozenset(ev.id for ev in plan.events)),
        (
            "frontend_route",
            _node_ids(graph, NodeType.FRONTEND_ROUTE),
            frozenset(r.id for r in plan.frontend_routes),
        ),
        (
            "frontend_interaction",
            _node_ids(graph, NodeType.FRONTEND_INTERACTION),
            frozenset(fi.id for fi in plan.frontend_interactions),
        ),
    )
    for label, graph_ids, plan_ids in checks:
        if graph_ids != plan_ids:
            findings.append(f"{label}-id-set-mismatch")
        elif graph_ids:
            evidence.append(f"{label}-ids:{len(graph_ids)}")

    causes_graph = frozenset(
        (edge.id, edge.source_id, edge.target_id)
        for edge in graph.edges.values()
        if edge.type == EdgeType.CAUSES_EFFECT
    )
    causes_plan = frozenset(
        (binding.edge_id, binding.source_id, binding.effect_id)
        for binding in plan.effect_bindings
    )
    if causes_graph != causes_plan:
        findings.append("causes-effect-bindings-mismatch")
    elif causes_graph:
        evidence.append(f"effect-bindings:{len(causes_graph)}")

    lossy_ids = tuple(
        sorted(
            nid
            for nid, node in graph.nodes.items()
            if node.type in _LOSSY_EXPLICIT_NODE_TYPES
        )
    )
    if lossy_ids:
        evidence.append(f"lossy-explicit-nodes:{len(lossy_ids)}")

    unknown_behavioral = [
        nid
        for nid, node in graph.nodes.items()
        if node.type not in _LOSSY_EXPLICIT_NODE_TYPES
        and node.type not in _BEHAVIORAL_NODE_TYPES
    ]
    if unknown_behavioral:
        findings.append(f"unlowered-node-types:{len(unknown_behavioral)}")

    return B04LoweringVerificationReport(
        passed=not findings,
        findings=tuple(findings),
        lossy_node_ids=lossy_ids,
        preserved_evidence=tuple(evidence),
    )


def verify_b04_lowering_for_revision(revision: ISRRevision) -> B04LoweringVerificationReport:
    """Lower, diff obligations, and verify deterministic re-lowering digest."""
    plan = isr_to_plan(revision)
    report = verify_b04_lowering_obligations(revision, plan)
    findings = list(report.findings)
    evidence = list(report.preserved_evidence)

    digest_a = compute_plan_digest(plan)
    plan_b = isr_to_plan(revision)
    digest_b = compute_plan_digest(plan_b)
    if digest_a != digest_b:
        findings.append("relowering-nondeterministic")
    else:
        evidence.append("relowering-digest-stable")

    return B04LoweringVerificationReport(
        passed=not findings,
        findings=tuple(findings),
        lossy_node_ids=report.lossy_node_ids,
        preserved_evidence=tuple(evidence),
    )
