"""plan_builder — intent → ISR revision → CompilationPlan wiring.

This module bridges the corpus workloads to the compiler pipeline,
producing a (CompilationPlan, ISRRevision) pair for each workload.
For Campaign A, this uses a deterministic seed-driven ISR construction.
"""
from __future__ import annotations
import hashlib
import json
from compiler.core.lowering import isr_to_plan
from compiler.core.plan import CompilationPlan
from isr.core.graph import Edge, EdgeType, ISRGraph, Node, NodeType
from isr.core.identity import Provenance
from isr.core.revision import ISRRevision


def _deterministic_seed(intent: str, category: str) -> str:
    return hashlib.sha256(f"{intent}:{category}".encode("utf-8")).hexdigest()[:8]


def build_plan_for(intent: str, category: str, seeds: list[str] | None = None) -> tuple[CompilationPlan, ISRRevision]:
    """Build a CompilationPlan from a workload intent.

    For Campaign A, generates a minimal ISR with one service, one data model,
    one event, and one security policy — deterministic from the intent.
    """
    seed = _deterministic_seed(intent, category)
    svc_id = f"service:{seed}"
    dm_id = f"dm:{seed}"
    ev_id = f"event:{seed}"
    sec_id = f"sec:{seed}"

    nodes: dict[str, Node] = {
        svc_id: Node(
            id=svc_id,
            type=NodeType.SERVICE,
            properties={"label": f"svc_{seed}"},
        ),
        dm_id: Node(
            id=dm_id,
            type=NodeType.DATA_MODEL,
            properties={"label": f"Entity_{seed}"},
        ),
        ev_id: Node(
            id=ev_id,
            type=NodeType.EVENT,
            properties={"label": f"Event_{seed}"},
        ),
        sec_id: Node(
            id=sec_id,
            type=NodeType.SECURITY_POLICY,
            properties={"label": f"policy_{seed}"},
        ),
    }
    edges: dict[str, Edge] = {
        "pers": Edge(id="pers", type=EdgeType.PERSISTS, source_id=svc_id, target_id=dm_id),
        "pub": Edge(id="pub", type=EdgeType.PUBLISHES, source_id=svc_id, target_id=ev_id),
        "sec": Edge(id="sec", type=EdgeType.SECURED_BY, source_id=svc_id, target_id=sec_id),
    }

    graph = ISRGraph(nodes=nodes, edges=edges)
    provenance = Provenance(
        created_by="campaign_a",
        created_at="2025-01-01T00:00:00Z",
    )
    revision = ISRRevision.create(
        system_id=f"cbc1-{category}",
        revision_id=f"rev-{seed}",
        schema_version="1.0",
        graph=graph,
        provenance=provenance,
    )

    plan = isr_to_plan(revision)
    return plan, revision
