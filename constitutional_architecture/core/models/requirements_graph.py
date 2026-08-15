"""
Requirements Graph — Intermediate representation between IntentModel and ArchitectureGenome.

Captures semantic relationships that nested objects cannot express:
- capabilities depend on other capabilities
- personas use capabilities
- quality attributes constrain capabilities
- compliance affects data domains
- operational constraints influence topology
- business goals map to architectural objectives

Enables: graph validation, conflict detection, dependency analysis, impact analysis,
graph-based evolution, and graph-aware fitness evaluation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, unique
from typing import Any, Dict, List, Optional, Set


# ─── Graph Types ─────────────────────────────────────────────────────────────

@unique
class NodeType(str, Enum):
    CAPABILITY = "capability"
    PERSONA = "persona"
    DATA_DOMAIN = "data_domain"
    INTEGRATION_POINT = "integration_point"
    QUALITY_ATTRIBUTE = "quality_attribute"
    COMPLIANCE_STANDARD = "compliance_standard"
    OPERATIONAL_CONSTRAINT = "operational_constraint"
    BUSINESS_GOAL = "business_goal"
    ARCHITECTURAL_OBJECTIVE = "architectural_objective"


@unique
class EdgeType(str, Enum):
    DEPENDS_ON = "depends_on"
    USES = "uses"
    CONSTRAINS = "constrains"
    AFFECTS = "affects"
    REQUIRES = "requires"
    CONFLICTS_WITH = "conflicts_with"
    ENABLES = "enables"
    SATISFIES = "satisfies"


# ─── Graph Elements ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class RequirementNode:
    id: str
    type: NodeType
    label: str
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RequirementEdge:
    source: str
    target: str
    type: EdgeType
    weight: float = 1.0
    properties: Dict[str, Any] = field(default_factory=dict)


# ─── Validation Results ──────────────────────────────────────────────────────

@dataclass
class GraphValidationIssue:
    severity: str  # error | warning | info
    message: str
    node_id: str = ""


@dataclass
class ImpactAnalysis:
    affected_nodes: List[str]
    description: str


# ─── The Graph ───────────────────────────────────────────────────────────────

class RequirementsGraph:
    """Directed, typed graph of requirements relationships.

    Supports:
    - Adding nodes and edges with type safety
    - Cycle detection
    - Dependency analysis (transitive closure)
    - Conflict detection
    - Impact analysis (what breaks if a node is removed)
    - Topological ordering
    - Graph validation
    """

    def __init__(self) -> None:
        self._nodes: Dict[str, RequirementNode] = {}
        self._edges: List[RequirementEdge] = []
        self._outgoing: Dict[str, List[RequirementEdge]] = {}
        self._incoming: Dict[str, List[RequirementEdge]] = {}

    # ── Mutation ──────────────────────────────────────────────────────────

    def add_node(self, node: RequirementNode) -> None:
        if node.id in self._nodes:
            raise ValueError(f"Node '{node.id}' already exists in graph")
        self._nodes[node.id] = node
        self._outgoing.setdefault(node.id, [])
        self._incoming.setdefault(node.id, [])

    def add_edge(self, edge: RequirementEdge) -> None:
        if edge.source not in self._nodes:
            raise ValueError(f"Source node '{edge.source}' not found in graph")
        if edge.target not in self._nodes:
            raise ValueError(f"Target node '{edge.target}' not found in graph")
        self._edges.append(edge)
        self._outgoing.setdefault(edge.source, []).append(edge)
        self._incoming.setdefault(edge.target, []).append(edge)

    # ── Accessors ─────────────────────────────────────────────────────────

    @property
    def nodes(self) -> Dict[str, RequirementNode]:
        return dict(self._nodes)

    @property
    def edges(self) -> List[RequirementEdge]:
        return list(self._edges)

    def get_node(self, node_id: str) -> Optional[RequirementNode]:
        return self._nodes.get(node_id)

    def get_outgoing(self, node_id: str) -> List[RequirementEdge]:
        return list(self._outgoing.get(node_id, []))

    def get_incoming(self, node_id: str) -> List[RequirementEdge]:
        return list(self._incoming.get(node_id, []))

    def get_nodes_by_type(self, node_type: NodeType) -> List[RequirementNode]:
        return [n for n in self._nodes.values() if n.type == node_type]

    def get_edges_by_type(self, edge_type: EdgeType) -> List[RequirementEdge]:
        return [e for e in self._edges if e.type == edge_type]

    # ── Analysis ──────────────────────────────────────────────────────────

    def detect_cycles(self) -> List[List[str]]:
        """Return all cycles in the dependency graph."""
        cycles: List[List[str]] = []
        visited: Set[str] = set()
        rec_stack: Set[str] = set()
        path: List[str] = []

        def dfs(node_id: str) -> None:
            visited.add(node_id)
            rec_stack.add(node_id)
            path.append(node_id)
            for edge in self._outgoing.get(node_id, []):
                if edge.type != EdgeType.DEPENDS_ON:
                    continue
                if edge.target not in visited:
                    dfs(edge.target)
                elif edge.target in rec_stack:
                    cycle_start = path.index(edge.target)
                    cycles.append(path[cycle_start:] + [edge.target])
            path.pop()
            rec_stack.remove(node_id)

        for nid in self._nodes:
            if nid not in visited:
                dfs(nid)

        return cycles

    def transitive_dependencies(self, node_id: str) -> Set[str]:
        """All nodes that the given node directly or indirectly depends on."""
        deps: Set[str] = set()
        stack = [node_id]
        while stack:
            current = stack.pop()
            for edge in self._outgoing.get(current, []):
                if edge.type == EdgeType.DEPENDS_ON and edge.target not in deps:
                    deps.add(edge.target)
                    stack.append(edge.target)
        return deps

    def transitive_dependents(self, node_id: str) -> Set[str]:
        """All nodes that directly or indirectly depend on the given node."""
        dependents: Set[str] = set()
        stack = [node_id]
        while stack:
            current = stack.pop()
            for edge in self._incoming.get(current, []):
                if edge.type == EdgeType.DEPENDS_ON and edge.source not in dependents:
                    dependents.add(edge.source)
                    stack.append(edge.source)
        return dependents

    def detect_conflicts(self) -> List[GraphValidationIssue]:
        """Detect conflicting constraints in the graph."""
        issues: List[GraphValidationIssue] = []
        for edge in self.get_edges_by_type(EdgeType.CONFLICTS_WITH):
            issues.append(GraphValidationIssue(
                severity="error",
                message=f"Conflict between '{edge.source}' and '{edge.target}'",
            ))
        return issues

    def impact_analysis(self, node_id: str) -> ImpactAnalysis:
        """What breaks if this node is removed."""
        affected = list(self.transitive_dependents(node_id))
        node = self._nodes.get(node_id)
        label = node.label if node else node_id
        return ImpactAnalysis(
            affected_nodes=affected,
            description=f"Removing '{label}' affects {len(affected)} dependent(s): {', '.join(affected[:5])}{'...' if len(affected) > 5 else ''}",
        )

    def topological_sort(self) -> List[str]:
        """Return nodes in dependency order (no depends_on edge goes backward)."""
        in_degree: Dict[str, int] = {nid: 0 for nid in self._nodes}
        for edge in self.get_edges_by_type(EdgeType.DEPENDS_ON):
            in_degree[edge.target] = in_degree.get(edge.target, 0) + 1

        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        result: List[str] = []

        while queue:
            node = queue.pop(0)
            result.append(node)
            for edge in self._outgoing.get(node, []):
                if edge.type == EdgeType.DEPENDS_ON:
                    in_degree[edge.target] -= 1
                    if in_degree[edge.target] == 0:
                        queue.append(edge.target)

        if len(result) != len(self._nodes):
            remaining = set(self._nodes.keys()) - set(result)
            raise ValueError(f"Cycle detected among: {remaining}")

        return result

    def validate(self) -> List[GraphValidationIssue]:
        """Run all validation checks."""
        issues: List[GraphValidationIssue] = []

        cycles = self.detect_cycles()
        if cycles:
            for cycle in cycles:
                issues.append(GraphValidationIssue(
                    severity="error",
                    message=f"Circular dependency detected: {' -> '.join(cycle)}",
                ))

        issues.extend(self.detect_conflicts())

        for nid, node in self._nodes.items():
            for edge in self._outgoing.get(nid, []):
                if edge.target not in self._nodes:
                    issues.append(GraphValidationIssue(
                        severity="error",
                        message=f"Edge '{nid}' -> '{edge.target}' references non-existent node",
                        node_id=nid,
                    ))

        return issues

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": {nid: {"type": n.type.value, "label": n.label, "properties": n.properties} for nid, n in self._nodes.items()},
            "edges": [{"source": e.source, "target": e.target, "type": e.type.value, "weight": e.weight} for e in self._edges],
        }
