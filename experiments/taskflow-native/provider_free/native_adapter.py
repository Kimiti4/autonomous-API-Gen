"""Provider-free adapter from canonical TaskFlow inputs to native requirement graph.

This adapter intentionally stops before SystemModel/ISR creation when the
snapshot omits mandatory semantics. It never imports the golden app or guesses
security, domain schemas, API contracts, or deployment choices.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Mapping

from tiannara.domain.models.requirement_graph import (
    EdgeKind,
    GraphProvenance,
    RequirementEdge,
    RequirementGraph,
    RequirementKind,
    RequirementNode,
    NodeProvenance,
)
from tiannara.domain.models.system_model import Priority
from tiannara.domain.models.semantic_resolution import (
    SemanticResolutionRecord,
    build_initial_resolution_record,
)


CAPABILITY_MAP: dict[str, tuple[str, ...]] = {
    "A user can access only workspaces to which they belong.": ("workspace-tenancy",),
    "Cross-workspace reads and writes fail closed.": ("workspace-tenancy",),
    "An assignee must belong to the task's workspace.": ("tasks", "workspace-tenancy"),
    "Owner-only operations cannot be performed by ordinary members.": ("rbac",),
    "Task/project/workspace relationships remain consistent.": ("tasks", "projects", "workspace-tenancy"),
    "Archived records do not reappear in normal active queries.": ("tasks", "projects"),
    "Authorization outcomes are deterministic and fail closed.": ("rbac", "workspace-tenancy"),
    "Requests explicitly declared idempotent do not create duplicate effects.": ("audit-trail",),
    "Security-sensitive mutations have a unique auditable effect identity.": ("audit-trail",),
    "Authentication sessions can be invalidated and invalidated sessions cannot continue to authorize requests.": ("authentication",),
    "Expose health/readiness information.": ("operational-observability",),
    "Produce structured operational/audit evidence.": ("operational-observability", "audit-trail"),
    "Support repeatable automated verification.": ("operational-observability",),
    "Be deployable in a reproducible environment.": ("operational-observability",),
    "Preserve enough provenance to trace each certified capability back to the specification.": ("audit-trail",),
}


@dataclass(frozen=True)
class NativeAdapterResult:
    graph: RequirementGraph
    problem_sha256: str
    acceptance_sha256: str
    semantic_resolutions: SemanticResolutionRecord
    system_model: None
    typed_isr: None
    generation_allowed: bool
    blockers: tuple[str, ...]
    traceability: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "tiannara.taskflow.native-adapter.v1",
            "problem_sha256": self.problem_sha256,
            "acceptance_sha256": self.acceptance_sha256,
            "requirement_graph": self.graph.model_dump(mode="json"),
            "requirement_graph_sha256": self.graph.content_hash(),
            "semantic_resolution_record": self.semantic_resolutions.model_dump(mode="json"),
            "unresolved_mandatory_semantics": list(self.semantic_resolutions.unresolved_fields()),
            "system_model": None,
            "typed_isr": None,
            "generation_allowed": self.generation_allowed,
            "certified": False,
            "provider_required": False,
            "network_calls": 0,
            "blockers": list(self.blockers),
            "traceability": self.traceability,
        }


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _stable_id(prefix: str, identity: str) -> str:
    return f"{prefix}-{_sha256(identity.encode('utf-8'))[:16].upper()}"


def _canonical_json(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def adapt_taskflow_snapshot(
    problem: str,
    acceptance: Mapping[str, Any],
    *,
    problem_source: str = "snapshot:inputs/experiments/taskflow-native/PROBLEM.md",
    acceptance_source: str = "snapshot:inputs/golden-projects/taskflow/ACCEPTANCE.json",
) -> NativeAdapterResult:
    """Build a stable native RequirementGraph; fail closed before typed ISR."""
    if not isinstance(problem, str) or not problem.strip():
        raise ValueError("problem must be a non-empty string")
    if not isinstance(acceptance, Mapping):
        raise TypeError("acceptance must be a JSON object")

    capabilities = acceptance.get("required_capabilities")
    gates = acceptance.get("quality_gates")
    negatives = acceptance.get("negative_cases")
    project_id = acceptance.get("project_id")
    if not isinstance(project_id, str) or not project_id.strip():
        raise ValueError("project_id must be a non-empty string")
    if not isinstance(capabilities, list) or not capabilities or any(
        not isinstance(item, str) or not item.strip() for item in capabilities
    ):
        raise ValueError("required_capabilities must be a non-empty list of names")
    if len(capabilities) != len(set(capabilities)):
        raise ValueError("required_capabilities contains duplicates")
    if not isinstance(gates, Mapping) or any(
        not isinstance(k, str) or not isinstance(v, bool) for k, v in gates.items()
    ):
        raise ValueError("quality_gates must map names to boolean values")
    if not isinstance(negatives, list) or any(
        not isinstance(item, str) or not item.strip() for item in negatives
    ):
        raise ValueError("negative_cases must be a list of non-empty strings")
    if len(negatives) != len(set(negatives)):
        raise ValueError("negative_cases contains duplicates")

    problem_bytes = problem.encode("utf-8")
    acceptance_bytes = _canonical_json(acceptance)
    problem_hash = _sha256(problem_bytes)
    acceptance_hash = _sha256(acceptance_bytes)
    graph_hash_seed = _sha256((problem_hash + ":" + acceptance_hash).encode("ascii"))
    graph_id = f"rg-taskflow-{graph_hash_seed[:16]}"

    nodes: list[RequirementNode] = []
    edges: list[RequirementEdge] = []
    trace: dict[str, Any] = {"capabilities": [], "problem_obligations": [], "quality_gates": [], "negative_cases": []}
    cap_ids: dict[str, str] = {}

    def add_node(
        *, prefix: str, identity: str, kind: RequirementKind, statement: str,
        source: str, pointer: str, priority: Priority = Priority.MUST,
        criteria: list[str] | None = None, rationale: str = "",
    ) -> str:
        node_id = _stable_id(prefix, identity)
        nodes.append(RequirementNode(
            id=node_id,
            kind=kind,
            statement=statement,
            priority=priority,
            acceptance_criteria=criteria or [],
            rationale=(rationale + " " if rationale else "") + f"Source: {source}#{pointer}",
            provenance=NodeProvenance(
                source=source,
                taxonomy_version="taskflow-native-adapter.v1",
                stratum=pointer,
                created_by="provider-free-snapshot-adapter",
            ),
        ))
        return node_id

    for index, name in enumerate(capabilities):
        node_id = add_node(
            prefix="CAP", identity=name, kind=RequirementKind.FUNCTIONAL,
            statement=f"Required capability: {name}", source=acceptance_source,
            pointer=f"/required_capabilities/{index}",
            criteria=["Capability implementation and evidence independently verified"],
            rationale="Registration or specification mapping alone is not evidence.",
        )
        cap_ids[name] = node_id
        trace["capabilities"].append({"name": name, "node_id": node_id, "source_pointer": f"/required_capabilities/{index}", "status": "UNKNOWN"})

    active_section: str | None = None
    allowed_sections = {"Security and correctness requirements", "Operational requirements"}
    for line_number, line in enumerate(problem.splitlines(), start=1):
        stripped = line.strip()
        if stripped.endswith(":") and not stripped.startswith("-"):
            heading = stripped[:-1]
            active_section = heading if heading in allowed_sections else None
            continue
        if not active_section or not stripped.startswith("- "):
            continue
        statement = stripped[2:].strip()
        identity = f"{line_number}:{statement}"
        node_id = add_node(
            prefix="REQ", identity=identity, kind=RequirementKind.CONSTRAINT,
            statement=statement, source=problem_source, pointer=f"L{line_number}",
            criteria=["Requirement behavior verified by an executable test or inspection"],
            rationale=f"Specification section: {active_section}.",
        )
        mapped = CAPABILITY_MAP.get(statement, ())
        mapped_ids = []
        for capability in mapped:
            if capability in cap_ids:
                edges.append(RequirementEdge(
                    source_id=node_id, target_id=cap_ids[capability],
                    kind=EdgeKind.DERIVES_FROM,
                    rationale="Explicit obligation-to-capability mapping; not implementation evidence.",
                ))
                mapped_ids.append(cap_ids[capability])
        trace["problem_obligations"].append({
            "statement": statement, "node_id": node_id, "source": problem_source,
            "line": line_number, "section": active_section,
            "mapped_capabilities": list(mapped), "mapped_node_ids": mapped_ids,
            "mapping_status": "MAPPED" if mapped and len(mapped_ids) == len(mapped) else "UNKNOWN",
            "verification_status": "UNKNOWN",
        })

    for name, enabled in sorted(gates.items()):
        if not enabled:
            continue
        node_id = add_node(
            prefix="GATE", identity=name, kind=RequirementKind.QUALITY,
            statement=f"Required quality gate: {name}", source=acceptance_source,
            pointer=f"/quality_gates/{name}",
            criteria=["Gate executed against this candidate and evidence retained"],
        )
        trace["quality_gates"].append({"name": name, "node_id": node_id, "source_pointer": f"/quality_gates/{name}", "status": "UNKNOWN"})

    for index, name in enumerate(negatives):
        node_id = add_node(
            prefix="NEG", identity=name, kind=RequirementKind.CONSTRAINT,
            statement=f"Negative case must be rejected safely: {name}",
            source=acceptance_source, pointer=f"/negative_cases/{index}",
            criteria=["Observed negative-case test passes against the generated candidate"],
        )
        trace["negative_cases"].append({"name": name, "node_id": node_id, "source_pointer": f"/negative_cases/{index}", "status": "UNKNOWN"})

    graph = RequirementGraph(
        graph_id=graph_id,
        nodes=nodes,
        edges=edges,
        provenance=GraphProvenance(
            origin="immutable_taskflow_snapshot",
            source_statement_hash=graph_hash_seed,
            taxonomy_version="taskflow-native-adapter.v1",
        ),
    )

    unmapped = [item["statement"] for item in trace["problem_obligations"] if item["mapping_status"] != "MAPPED"]
    blockers = [
        "TaskFlow snapshot does not define domain entity fields, identity rules, relationship cardinalities, or lifecycle semantics.",
        "Complete role-permission matrix and session invalidation contract are not fully specified.",
        "Concrete API request/response schemas and frontend interaction contracts are not specified.",
        "The native SystemModel schema defaults security, consistency, infrastructure, deployment, and testing postures; unknowns cannot safely inherit those defaults.",
        "Required capabilities, quality gates, and negative cases have not been implemented and independently verified by this adapter.",
    ]
    if unmapped:
        blockers.append(f"{len(unmapped)} problem obligation(s) lack an explicit capability mapping.")
    return NativeAdapterResult(
        graph=graph,
        problem_sha256=problem_hash,
        acceptance_sha256=acceptance_hash,
        semantic_resolutions=build_initial_resolution_record(graph),
        system_model=None,
        typed_isr=None,
        generation_allowed=False,
        blockers=tuple(blockers),
        traceability=trace,
    )
