"""
ISR Graph — Typed, directed, attributed graph representation.

The ISR is internally represented as a single graph, with different
subsystems accessing it through specialised projections (views).
The graph provides structural navigation, edge attribute queries,
subgraph extraction, reachability analysis, and dependency resolution.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Any, Callable
from collections import defaultdict

from constitutional_architecture.isr.model import (
    System, Module, Entity, Service, Workflow, Policy,
    Interface, Event, Deployment, Constraint,
    NodeType, EdgeType, CompletenessLevel,
    Relationship, ServiceDependency
)


@dataclass(frozen=True)
class ISRNode:
    """A node in the ISR graph, wrapping a model object with its ID."""
    node_id: str
    node_type: NodeType
    module_name: Optional[str]
    parent_id: Optional[str]
    data: Any  # The actual model object (Entity, Service, etc.)
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ISREdge:
    """A typed edge in the ISR graph between two nodes."""
    source_id: str
    target_id: str
    edge_type: EdgeType
    cardinality: str = "one_to_one"
    attributes: Dict[str, Any] = field(default_factory=dict)


class DependencyGraph:
    """A view of the ISR focused solely on dependency relationships.

    Provides cycle detection, dependency depth analysis, and
    dependency chain traversal.
    """

    def __init__(self, adj_list: Dict[str, List[Tuple[str, EdgeType, Dict]]]):
        self._adj = adj_list
        self._node_set = set(adj_list.keys())
        for targets in adj_list.values():
            for t, _, _ in targets:
                self._node_set.add(t)

    def has_cycle(self) -> bool:
        """Check if the dependency graph contains a cycle."""
        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            for target, _, _ in self._adj.get(node, []):
                if target not in visited:
                    if dfs(target):
                        return True
                elif target in rec_stack:
                    return True
            rec_stack.discard(node)
            return False

        for node in self._node_set:
            if node not in visited:
                if dfs(node):
                    return True
        return False

    def get_dependency_depth(self, node_id: str) -> int:
        """Get the maximum dependency chain depth from a node."""
        visited: Set[str] = set()

        def dfs(node: str, depth: int) -> int:
            if node in visited:
                return depth
            visited.add(node)
            max_depth = depth
            for target, _, _ in self._adj.get(node, []):
                child_depth = dfs(target, depth + 1)
                max_depth = max(max_depth, child_depth)
            visited.discard(node)
            return max_depth

        return dfs(node_id, 0)

    def get_all_dependencies(self, node_id: str) -> Set[str]:
        """Get all transitive dependencies of a node."""
        result: Set[str] = set()
        stack = [node_id]
        while stack:
            current = stack.pop()
            for target, _, _ in self._adj.get(current, []):
                if target not in result:
                    result.add(target)
                    stack.append(target)
        return result

    def get_dependents(self, node_id: str) -> Set[str]:
        """Get all nodes that depend on this node (reverse lookup)."""
        result: Set[str] = set()
        for source, targets in self._adj.items():
            for target, _, _ in targets:
                if target == node_id:
                    result.add(source)
        return result

    @property
    def node_count(self) -> int:
        return len(self._node_set)

    @property
    def edge_count(self) -> int:
        return sum(len(t) for t in self._adj.values())


class ISRGraph:
    """The complete typed, directed, attributed ISR graph.

    This is the constitutional source of truth. Every subsystem
    derives its view from this graph. The graph is immutable:
    all mutations produce a new graph instance.
    """

    def __init__(self, system: System):
        self._system = system
        self._nodes: Dict[str, ISRNode] = {}
        self._edges: List[ISREdge] = []
        self._adj: Dict[str, List[Tuple[str, EdgeType, Dict]]] = defaultdict(list)
        self._reverse_adj: Dict[str, List[Tuple[str, EdgeType, Dict]]] = defaultdict(list)
        self._build_graph()

    def _add_node(self, node: ISRNode):
        """Add a node to the graph."""
        self._nodes[node.node_id] = node

    def _add_edge(self, edge: ISREdge):
        """Add a typed edge to the graph."""
        self._edges.append(edge)
        self._adj[edge.source_id].append((edge.target_id, edge.edge_type, edge.attributes))
        self._reverse_adj[edge.target_id].append((edge.source_id, edge.edge_type, edge.attributes))

    def _build_graph(self):
        """Build the full graph from the System model."""
        sys_id = f"system:{self._system.name}"
        self._add_node(ISRNode(
            node_id=sys_id,
            node_type=NodeType.SYSTEM,
            module_name=None,
            parent_id=None,
            data=self._system,
        ))

        for module in self._system.modules:
            mod_id = f"module:{module.name}"
            self._add_node(ISRNode(
                node_id=mod_id,
                node_type=NodeType.MODULE,
                module_name=module.name,
                parent_id=sys_id,
                data=module,
            ))
            self._add_edge(ISREdge(
                source_id=sys_id,
                target_id=mod_id,
                edge_type=EdgeType.OWNS,
            ))

            # Entities
            for entity in module.entities:
                ent_id = f"entity:{module.name}:{entity.name}"
                self._add_node(ISRNode(
                    node_id=ent_id,
                    node_type=NodeType.ENTITY,
                    module_name=module.name,
                    parent_id=mod_id,
                    data=entity,
                ))
                self._add_edge(ISREdge(
                    source_id=mod_id,
                    target_id=ent_id,
                    edge_type=EdgeType.OWNS,
                ))

                # Entity relationships (references to other entities)
                for rel in entity.relationships:
                    target_mod = module.name
                    target_ent_id = f"entity:{target_mod}:{rel.target_entity_id}"
                    if target_ent_id in self._nodes:
                        self._add_edge(ISREdge(
                            source_id=ent_id,
                            target_id=target_ent_id,
                            edge_type=EdgeType.REFERENCES,
                            cardinality=rel.relationship_type,
                            attributes={"type": rel.relationship_type},
                        ))

            # Services
            for service in module.services:
                svc_id = f"service:{module.name}:{service.name}"
                self._add_node(ISRNode(
                    node_id=svc_id,
                    node_type=NodeType.SERVICE,
                    module_name=module.name,
                    parent_id=mod_id,
                    data=service,
                ))
                self._add_edge(ISREdge(
                    source_id=mod_id,
                    target_id=svc_id,
                    edge_type=EdgeType.OWNS,
                ))

                # Service dependencies
                for dep in service.dependencies:
                    target_mod = module.name
                    target_svc_id = f"service:{target_mod}:{dep.target_service_id}"
                    if target_svc_id in self._nodes:
                        self._add_edge(ISREdge(
                            source_id=svc_id,
                            target_id=target_svc_id,
                            edge_type=EdgeType.DEPENDS_ON,
                            attributes={
                                "dependency_type": dep.dependency_type,
                                "is_required": dep.is_required,
                                "description": dep.description,
                            },
                        ))

                # Service emits events
                for event_name in service.emitted_events:
                    event_id = f"event:{module.name}:{event_name}"
                    if event_id in self._nodes:
                        self._add_edge(ISREdge(
                            source_id=svc_id,
                            target_id=event_id,
                            edge_type=EdgeType.EMITS,
                        ))

                # Service consumes events
                for event_name in service.consumed_events:
                    # Events might be in other modules; search all
                    for other_mod in self._system.modules:
                        for other_event in other_mod.events:
                            if other_event.name == event_name:
                                target_event_id = f"event:{other_mod.name}:{event_name}"
                                if target_event_id in self._nodes:
                                    self._add_edge(ISREdge(
                                        source_id=svc_id,
                                        target_id=target_event_id,
                                        edge_type=EdgeType.CONSUMES,
                                    ))

            # Events
            for event in module.events:
                evt_id = f"event:{module.name}:{event.name}"
                self._add_node(ISRNode(
                    node_id=evt_id,
                    node_type=NodeType.EVENT,
                    module_name=module.name,
                    parent_id=mod_id,
                    data=event,
                ))
                self._add_edge(ISREdge(
                    source_id=mod_id,
                    target_id=evt_id,
                    edge_type=EdgeType.OWNS,
                ))

            # Workflows
            for workflow in module.workflows:
                wf_id = f"workflow:{module.name}:{workflow.name}"
                self._add_node(ISRNode(
                    node_id=wf_id,
                    node_type=NodeType.WORKFLOW,
                    module_name=module.name,
                    parent_id=mod_id,
                    data=workflow,
                ))
                self._add_edge(ISREdge(
                    source_id=mod_id,
                    target_id=wf_id,
                    edge_type=EdgeType.OWNS,
                ))

                # Workflow orchestrates services (via transition/state actions)
                for state in workflow.states:
                    for action_name in state.entry_actions + state.exit_actions:
                        for svc_node in self.get_nodes_by_type(NodeType.SERVICE):
                            svc: Service = svc_node.data
                            for op in svc.operations:
                                if op.name == action_name:
                                    self._add_edge(ISREdge(
                                        source_id=wf_id,
                                        target_id=svc_node.node_id,
                                        edge_type=EdgeType.ORCHESTRATES,
                                    ))
                for transition in workflow.transitions:
                    for action_name in transition.actions:
                        for svc_node in self.get_nodes_by_type(NodeType.SERVICE):
                            svc: Service = svc_node.data
                            for op in svc.operations:
                                if op.name == action_name:
                                    self._add_edge(ISREdge(
                                        source_id=wf_id,
                                        target_id=svc_node.node_id,
                                        edge_type=EdgeType.ORCHESTRATES,
                                    ))

            # Policies
            for policy in module.policies:
                pol_id = f"policy:{module.name}:{policy.name}"
                self._add_node(ISRNode(
                    node_id=pol_id,
                    node_type=NodeType.POLICY,
                    module_name=module.name,
                    parent_id=mod_id,
                    data=policy,
                ))
                self._add_edge(ISREdge(
                    source_id=mod_id,
                    target_id=pol_id,
                    edge_type=EdgeType.OWNS,
                ))

                # Policy constrains interfaces
                for iface in module.interfaces:
                    if iface.secured_by_policy_id == policy.name:
                        iface_id = f"interface:{module.name}:{iface.name}"
                        self._add_edge(ISREdge(
                            source_id=pol_id,
                            target_id=iface_id,
                            edge_type=EdgeType.CONSTRAINS,
                        ))

            # Interfaces
            for iface in module.interfaces:
                iface_id = f"interface:{module.name}:{iface.name}"
                self._add_node(ISRNode(
                    node_id=iface_id,
                    node_type=NodeType.INTERFACE,
                    module_name=module.name,
                    parent_id=mod_id,
                    data=iface,
                ))
                self._add_edge(ISREdge(
                    source_id=mod_id,
                    target_id=iface_id,
                    edge_type=EdgeType.OWNS,
                ))

                # Interface secured-by policy
                if iface.secured_by_policy_id:
                    pol_id = f"policy:{module.name}:{iface.secured_by_policy_id}"
                    if pol_id in self._nodes:
                        self._add_edge(ISREdge(
                            source_id=iface_id,
                            target_id=pol_id,
                            edge_type=EdgeType.SECURED_BY,
                            attributes={"auth_strategy": "default"},
                        ))

        # System-level deployment
        if self._system.deployment:
            dep_id = "deployment:system"
            self._add_node(ISRNode(
                node_id=dep_id,
                node_type=NodeType.DEPLOYMENT,
                module_name=None,
                parent_id=sys_id,
                data=self._system.deployment,
            ))
            self._add_edge(ISREdge(
                source_id=sys_id,
                target_id=dep_id,
                edge_type=EdgeType.OWNS,
            ))

        # System-level constraints
        for constraint in self._system.constraints:
            con_id = f"constraint:{constraint.name}"
            self._add_node(ISRNode(
                node_id=con_id,
                node_type=NodeType.CONSTRAINT,
                module_name=None,
                parent_id=sys_id,
                data=constraint,
            ))
            self._add_edge(ISREdge(
                source_id=sys_id,
                target_id=con_id,
                edge_type=EdgeType.OWNS,
            ))

    # ─── Graph Queries ───

    @property
    def system(self) -> System:
        """Get the root System object."""
        return self._system

    @property
    def nodes(self) -> Dict[str, ISRNode]:
        """Get all nodes by ID."""
        return dict(self._nodes)

    @property
    def edges(self) -> List[ISREdge]:
        """Get all edges."""
        return list(self._edges)

    def get_node(self, node_id: str) -> Optional[ISRNode]:
        """Get a node by its ID."""
        return self._nodes.get(node_id)

    def get_nodes_by_type(self, node_type: NodeType) -> List[ISRNode]:
        """Get all nodes of a specific type."""
        return [n for n in self._nodes.values() if n.node_type == node_type]

    def get_edges_from(self, node_id: str, edge_type: Optional[EdgeType] = None) -> List[ISREdge]:
        """Get all edges from a node, optionally filtered by type."""
        results = []
        for edge in self._edges:
            if edge.source_id == node_id:
                if edge_type is None or edge.edge_type == edge_type:
                    results.append(edge)
        return results

    def get_edges_to(self, node_id: str, edge_type: Optional[EdgeType] = None) -> List[ISREdge]:
        """Get all edges to a node, optionally filtered by type."""
        results = []
        for edge in self._edges:
            if edge.target_id == node_id:
                if edge_type is None or edge.edge_type == edge_type:
                    results.append(edge)
        return results

    def get_dependency_graph(self) -> DependencyGraph:
        """Get the dependency subgraph (depends-on edges only)."""
        dep_adj: Dict[str, List[Tuple[str, EdgeType, Dict]]] = defaultdict(list)
        for edge in self._edges:
            if edge.edge_type == EdgeType.DEPENDS_ON:
                dep_adj[edge.source_id].append(
                    (edge.target_id, edge.edge_type, edge.attributes)
                )
        return DependencyGraph(dep_adj)

    def compute_completeness_level(self) -> CompletenessLevel:
        """Determine the completeness level of this ISR.

        L0: System name + module names
        L1: + entities and relationships
        L2: + services, operations, events, workflows
        L3: + policies, security
        L4: + deployment, scaling, networking
        L5: Complete
        """
        has_entities = len(self.get_nodes_by_type(NodeType.ENTITY)) > 0
        has_services = len(self.get_nodes_by_type(NodeType.SERVICE)) > 0
        has_workflows = len(self.get_nodes_by_type(NodeType.WORKFLOW)) > 0
        has_policies = len(self.get_nodes_by_type(NodeType.POLICY)) > 0
        has_events = len(self.get_nodes_by_type(NodeType.EVENT)) > 0
        has_deployment = len(self.get_nodes_by_type(NodeType.DEPLOYMENT)) > 0

        modules = self.get_nodes_by_type(NodeType.MODULE)
        if not modules:
            return CompletenessLevel.L0_SKELETON

        if not has_entities:
            return CompletenessLevel.L0_SKELETON
        if not has_services:
            return CompletenessLevel.L1_STRUCTURAL
        if not has_workflows and not has_events:
            return CompletenessLevel.L1_STRUCTURAL
        if not has_policies:
            return CompletenessLevel.L2_BEHAVIOURAL
        if not has_deployment:
            return CompletenessLevel.L3_POLICY

        return CompletenessLevel.L5_COMPLETE

    # ─── Views ───

    def get_structural_view(self) -> dict:
        """Structural View: module relationships, dependencies, interfaces."""
        view = {
            "system": self._system.name,
            "modules": [],
        }
        for mod_node in self.get_nodes_by_type(NodeType.MODULE):
            mod_info = {
                "name": mod_node.module_name,
                "entities": [],
                "services": [],
                "interfaces": [],
                "dependencies": [],
                "dependents": [],
            }

            for edge in self.get_edges_from(mod_node.node_id):
                target = self._nodes.get(edge.target_id)
                if target:
                    if target.node_type == NodeType.ENTITY:
                        mod_info["entities"].append(target.node_id)
                    elif target.node_type == NodeType.SERVICE:
                        mod_info["services"].append(target.node_id)
                    elif target.node_type == NodeType.INTERFACE:
                        mod_info["interfaces"].append(target.node_id)

            # External dependencies (depends-on edges crossing modules)
            for svc_node in self.get_nodes_by_type(NodeType.SERVICE):
                if svc_node.module_name != mod_node.module_name:
                    continue
                for edge in self.get_edges_from(svc_node.node_id, EdgeType.DEPENDS_ON):
                    target = self._nodes.get(edge.target_id)
                    if target and target.module_name != mod_node.module_name:
                        mod_info["dependencies"].append({
                            "service": svc_node.node_id,
                            "target": target.node_id,
                            "target_module": target.module_name,
                        })

            # Dependents
            for svc_node in self.get_nodes_by_type(NodeType.SERVICE):
                if svc_node.module_name != mod_node.module_name:
                    for edge in self.get_edges_from(svc_node.node_id, EdgeType.DEPENDS_ON):
                        target = self._nodes.get(edge.target_id)
                        if target and target.module_name == mod_node.module_name:
                            mod_info["dependents"].append({
                                "service": svc_node.node_id,
                                "source_module": svc_node.module_name,
                            })

            view["modules"].append(mod_info)

        return view

    def get_security_view(self) -> dict:
        """Security View: policies, threat boundaries, trust zones."""
        view = {
            "policies": [],
            "secured_interfaces": [],
            "roles": set(),
        }
        for pol_node in self.get_nodes_by_type(NodeType.POLICY):
            policy = pol_node.data
            view["policies"].append({
                "name": policy.name,
                "module": pol_node.module_name,
                "strategy": policy.strategy,
                "roles": policy.roles,
                "rules": [r.name for r in policy.rules],
            })
            for role in policy.roles:
                view["roles"].add(role)

            # Interfaces secured by this policy
            for edge in self.get_edges_to(pol_node.node_id, EdgeType.SECURED_BY):
                source = self._nodes.get(edge.source_id)
                if source:
                    view["secured_interfaces"].append(source.node_id)

        view["roles"] = list(view["roles"])
        return view

    def get_deployment_view(self) -> dict:
        """Deployment View: infrastructure, scaling, networking, secrets."""
        view = {
            "deployments": [],
            "infrastructure_requirements": [],
        }
        for dep_node in self.get_nodes_by_type(NodeType.DEPLOYMENT):
            dep = dep_node.data
            view["deployments"].append({
                "name": dep.name,
                "scaling": {
                    "min": dep.scaling.min_instances,
                    "max": dep.scaling.max_instances,
                    "policy": dep.scaling.strategy.value,
                },
                "networking": {
                    "ports": [dep.networking.port],
                    "tls": dep.networking.tls_required,
                    "ingress": "public" if dep.networking.expose_publicly else "internal",
                },
                "storage": {
                    "type": "persistent" if dep.storage.persistent_storage_required else "ephemeral",
                    "size_gb": dep.storage.storage_size_gb,
                },
                "monitoring": {
                    "health_check": dep.monitoring.health_check_path,
                    "metrics": dep.monitoring.metrics_enabled,
                    "tracing": dep.monitoring.tracing_enabled,
                },
            })

        return view

    def get_api_view(self) -> dict:
        """API View: interfaces, contracts, versions, rate limits."""
        view = {"apis": []}
        for iface_node in self.get_nodes_by_type(NodeType.INTERFACE):
            iface = iface_node.data
            api_info = {
                "name": iface.name,
                "module": iface_node.module_name,
                "type": iface.interface_type,
                "version": iface.version,
                "internal": iface.internal,
                "endpoints": [
                    {"path": ep.path, "method": ep.method, "operation": ep.operation}
                    for ep in iface.endpoints
                ],
                "security": [
                    {"policy": sb.policy_name, "strategy": sb.auth_strategy}
                    for sb in iface.security_bindings
                ],
            }
            view["apis"].append(api_info)
        return view

    def get_workflow_view(self) -> dict:
        """Workflow View: business processes, events, state machines."""
        view = {"workflows": []}
        for wf_node in self.get_nodes_by_type(NodeType.WORKFLOW):
            wf = wf_node.data
            wf_info = {
                "name": wf.name,
                "module": wf_node.module_name,
                "states": [
                    {"name": s.name, "initial": s.is_initial, "terminal": s.is_terminal}
                    for s in wf.states
                ],
                "transitions": [
                    {"from": t.from_state, "to": t.to_state, "action": t.action}
                    for t in wf.transitions
                ],
            }
            view["workflows"].append(wf_info)
        return view

    def compute_hash(self) -> str:
        """Compute a content-hash for this ISR graph.

        Used for versioning, lineage tracking, and immutability.
        """
        # Collect all content into a deterministic structure
        content = {
            "system": self._system.name,
            "modules": [],
        }
        for mod in self._system.modules:
            mod_entry = {
                "name": mod.name,
                "entity_count": len(mod.entities),
                "service_count": len(mod.services),
                "interface_count": len(mod.interfaces),
            }
            content["modules"].append(mod_entry)

        # Add all edges in sorted order for determinism
        edges_sorted = sorted(
            [(e.source_id, e.target_id, e.edge_type.value) for e in self._edges]
        )
        content["edges"] = edges_sorted

        raw = json.dumps(content, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def clone_with_system(self, new_system: System) -> "ISRGraph":
        """Create a new graph from a modified System (immutable pattern)."""
        return ISRGraph(new_system)