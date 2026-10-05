"""Project-wide mutation impact intelligence for ESAP Bucket 3.8.

This module plans mutation impact before implementation. It is implementation-
agnostic: callers provide a governed dependency graph and the engine computes
a deterministic transitive impact boundary plus verification obligations that
must be reconsidered.

The engine never mutates the project and never authorizes a mutation. An impact
plan is evidence about scope, not evidence that the proposed change is correct.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Iterable, Literal

Layer = Literal[
    "requirement", "architecture", "backend", "frontend", "api", "contract",
    "test", "documentation", "deployment", "other",
]

_VALID_LAYERS = {
    "requirement", "architecture", "backend", "frontend", "api", "contract",
    "test", "documentation", "deployment", "other",
}


@dataclass(frozen=True)
class ProjectNode:
    node_id: str
    layer: Layer
    obligation_ids: tuple[str, ...] = ()
    verification_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.node_id.strip():
            raise ValueError("node-id-required")
        if self.layer not in _VALID_LAYERS:
            raise ValueError("invalid-node-layer")
        if len(set(self.obligation_ids)) != len(self.obligation_ids):
            raise ValueError("duplicate-node-obligation")
        if len(set(self.verification_ids)) != len(self.verification_ids):
            raise ValueError("duplicate-node-verification")


@dataclass(frozen=True)
class MutationRequest:
    mutation_id: str
    target_node_ids: tuple[str, ...]
    reason: str
    requested_scope: str = "target-and-dependent"
    max_depth: int | None = None

    def __post_init__(self) -> None:
        if not self.mutation_id.strip():
            raise ValueError("mutation-id-required")
        if not self.target_node_ids:
            raise ValueError("mutation-target-required")
        if len(set(self.target_node_ids)) != len(self.target_node_ids):
            raise ValueError("duplicate-mutation-target")
        if not self.reason.strip():
            raise ValueError("mutation-reason-required")
        if self.requested_scope not in {"target-only", "target-and-dependent"}:
            raise ValueError("invalid-mutation-scope")
        if self.max_depth is not None and self.max_depth < 0:
            raise ValueError("invalid-mutation-depth")


@dataclass(frozen=True)
class ImpactPlan:
    mutation_id: str
    target_node_ids: tuple[str, ...]
    direct_impact_node_ids: tuple[str, ...]
    transitive_impact_node_ids: tuple[str, ...]
    affected_layers: tuple[Layer, ...]
    affected_obligation_ids: tuple[str, ...]
    required_verification_ids: tuple[str, ...]
    missing_dependency_nodes: tuple[str, ...]
    bounded: bool
    plan_digest: str

    @property
    def affected_node_ids(self) -> tuple[str, ...]:
        return self.transitive_impact_node_ids

    @property
    def safe_to_apply(self) -> bool:
        # Scope discovery never proves mutation safety.
        return False


class MutationImpactEngine:
    """Deterministic dependency-closure planner.

    Dependencies are expressed as dependent -> dependency pairs. A mutation to
    a dependency therefore impacts every node that transitively depends on it.
    Planning is read-only and cannot itself mutate or authorize a change.
    """

    def __init__(
        self,
        *,
        project_id: str,
        nodes: Iterable[ProjectNode] = (),
        dependencies: Iterable[tuple[str, str]] = (),
    ) -> None:
        if not project_id.strip():
            raise ValueError("project-id-required")
        self.project_id = project_id
        self._nodes: dict[str, ProjectNode] = {}
        self._dependents: dict[str, set[str]] = {}

        for node in nodes:
            self.add_node(node)
        for dependent, dependency in dependencies:
            self.add_dependency(dependent, dependency)

    def add_node(self, node: ProjectNode) -> None:
        if node.node_id in self._nodes:
            raise ValueError("duplicate-node-id")
        self._nodes[node.node_id] = node
        self._dependents.setdefault(node.node_id, set())

    def add_dependency(self, dependent_node_id: str, dependency_node_id: str) -> None:
        self._require_node(dependent_node_id)
        self._require_node(dependency_node_id)
        if dependent_node_id == dependency_node_id:
            raise ValueError("self-dependency-rejected")
        self._dependents.setdefault(dependency_node_id, set()).add(dependent_node_id)

    def plan(self, request: MutationRequest) -> ImpactPlan:
        if any(node_id not in self._nodes for node_id in request.target_node_ids):
            raise ValueError("unknown-mutation-target")

        targets = tuple(sorted(request.target_node_ids))
        direct: set[str] = set()
        impacted: set[str] = set(targets)
        frontier: list[tuple[str, int]] = [(node_id, 0) for node_id in targets]
        bounded = True

        while frontier:
            current, depth = frontier.pop(0)
            dependents = sorted(self._dependents.get(current, ()))
            if request.max_depth is not None and depth >= request.max_depth:
                if dependents:
                    bounded = False
                continue
            for dependent in dependents:
                if dependent not in impacted:
                    impacted.add(dependent)
                    if depth == 0:
                        direct.add(dependent)
                    frontier.append((dependent, depth + 1))

        if request.requested_scope == "target-only":
            impacted = set(targets)
            direct = set()
            bounded = True

        ordered_impacted = tuple(sorted(impacted))
        layers = tuple(sorted({self._nodes[node_id].layer for node_id in impacted}))
        obligations = tuple(sorted({
            obligation_id
            for node_id in impacted
            for obligation_id in self._nodes[node_id].obligation_ids
        }))
        verifications = tuple(sorted({
            verification_id
            for node_id in impacted
            for verification_id in self._nodes[node_id].verification_ids
        }))

        payload = {
            "schema_version": "esap.mutation-impact.v1",
            "project_id": self.project_id,
            "mutation_id": request.mutation_id,
            "targets": targets,
            "direct": tuple(sorted(direct)),
            "transitive": ordered_impacted,
            "layers": layers,
            "obligations": obligations,
            "verifications": verifications,
            "bounded": bounded,
            "scope": request.requested_scope,
            "max_depth": request.max_depth,
        }
        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

        return ImpactPlan(
            mutation_id=request.mutation_id,
            target_node_ids=targets,
            direct_impact_node_ids=tuple(sorted(direct)),
            transitive_impact_node_ids=ordered_impacted,
            affected_layers=layers,
            affected_obligation_ids=obligations,
            required_verification_ids=verifications,
            missing_dependency_nodes=(),
            bounded=bounded,
            plan_digest=digest,
        )

    def _require_node(self, node_id: str) -> ProjectNode:
        if node_id not in self._nodes:
            raise ValueError("unknown-dependency-node")
        return self._nodes[node_id]
