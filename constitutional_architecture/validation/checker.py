"""
Architectural Type Checker

The validation engine is not merely a graph correctness checker. It is an
architectural type checker analogous to the semantic analysis phase of a
compiler. It performs multiple analysis passes to ensure architectural
correctness.

Passes:
1. Structural validation — graph well-formedness, cardinality, acyclicity
2. Type validation — edge-node compatibility per the type rules
3. Reference resolution — all identifiers resolve to existing nodes
4. Reachability analysis — all workflow states reachable; no orphaned nodes
5. Permission consistency — all referenced permissions defined in policies
6. Dependency satisfaction — all declared dependencies exist and are accessible
7. Completeness check — ISR meets minimum level for intended operation
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Any

from constitutional_architecture.isr.isr_graph import ISRGraph, ISRNode, ISREdge
from constitutional_architecture.isr.legacy_model import Severity
from constitutional_architecture.isr.model import CompletenessLevel, EdgeType, NodeType


@dataclass(frozen=True)
class ValidationIssue:
    """A single validation issue found during type checking."""
    severity: Severity
    message: str
    node_id: Optional[str] = None
    edge_index: Optional[int] = None
    pass_name: str = "unknown"
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ValidationResult:
    """The complete result of architectural type checking."""
    passed: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    completeness_level: CompletenessLevel = CompletenessLevel.L0_SKELETON
    summary: Dict[str, int] = field(default_factory=dict)

    @property
    def errors(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == Severity.ERROR]

    @property
    def warnings(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == Severity.WARNING]

    @property
    def infos(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == Severity.INFO]


class ArchitecturalTypeChecker:
    """Architectural type checker for ISR graphs.

    Performs the 7 defined analysis passes and produces a validation result
    that either accepts or rejects the ISR.
    """

    # ─── Type Rules Matrix ───
    # Defines which source-node → edge → target-node combinations are valid.
    # Format: {edge_type: {source_type: [valid_target_types]}}
    _TYPE_RULES: Dict[EdgeType, Dict[NodeType, List[NodeType]]] = {
        EdgeType.OWNS: {
            NodeType.SYSTEM: [NodeType.MODULE, NodeType.DEPLOYMENT, NodeType.CONSTRAINT],
            NodeType.MODULE: [NodeType.ENTITY, NodeType.SERVICE, NodeType.WORKFLOW,
                              NodeType.POLICY, NodeType.INTERFACE, NodeType.EVENT],
        },
        EdgeType.DEPENDS_ON: {
            NodeType.SERVICE: [NodeType.SERVICE],
        },
        EdgeType.EMITS: {
            NodeType.SERVICE: [NodeType.EVENT],
        },
        EdgeType.CONSUMES: {
            NodeType.SERVICE: [NodeType.EVENT],
        },
        EdgeType.REFERENCES: {
            NodeType.ENTITY: [NodeType.ENTITY],
        },
        EdgeType.IMPLEMENTS: {
            NodeType.SERVICE: [NodeType.INTERFACE],
        },
        EdgeType.SECURED_BY: {
            NodeType.INTERFACE: [NodeType.POLICY],
        },
        EdgeType.DEPLOYS_TO: {
            NodeType.SERVICE: [NodeType.DEPLOYMENT],
            NodeType.MODULE: [NodeType.DEPLOYMENT],
        },
        EdgeType.ORCHESTRATES: {
            NodeType.WORKFLOW: [NodeType.SERVICE],
        },
        EdgeType.CONSTRAINS: {
            NodeType.POLICY: [NodeType.INTERFACE, NodeType.SERVICE],
            NodeType.CONSTRAINT: [NodeType.MODULE, NodeType.SERVICE, NodeType.INTERFACE],
        },
    }

    def __init__(self):
        self._issues: List[ValidationIssue] = []

    def _issue(self, severity: Severity, message: str,
               node_id: Optional[str] = None, edge_index: Optional[int] = None,
               pass_name: str = "unknown", details: Optional[Dict] = None):
        self._issues.append(ValidationIssue(
            severity=severity,
            message=message,
            node_id=node_id,
            edge_index=edge_index,
            pass_name=pass_name,
            details=details or {},
        ))

    def validate(self, graph: ISRGraph,
                 minimum_level: CompletenessLevel = CompletenessLevel.L0_SKELETON) -> ValidationResult:
        """Run all validation passes on an ISR graph."""
        self._issues = []

        # Pass 1: Structural validation
        self._pass_structural(graph)

        # Pass 2: Type validation (edge-node compatibility)
        self._pass_type_validation(graph)

        # Pass 3: Reference resolution
        self._pass_reference_resolution(graph)

        # Pass 4: Reachability analysis
        self._pass_reachability(graph)

        # Pass 5: Permission consistency
        self._pass_permission_consistency(graph)

        # Pass 6: Dependency satisfaction
        self._pass_dependency_satisfaction(graph)

        # Pass 7: Completeness check
        completeness = self._pass_completeness(graph, minimum_level)

        errors = len([i for i in self._issues if i.severity == Severity.ERROR])
        warnings = len([i for i in self._issues if i.severity == Severity.WARNING])
        infos = len([i for i in self._issues if i.severity == Severity.INFO])

        return ValidationResult(
            passed=(errors == 0),
            issues=self._issues,
            completeness_level=completeness,
            summary={
                "errors": errors,
                "warnings": warnings,
                "infos": infos,
                "total_passes": 7,
            },
        )

    # ─── Pass 1: Structural Validation ───

    def _pass_structural(self, graph: ISRGraph):
        """Validate graph well-formedness, cardinality, and acyclicity."""
        # Check for empty system
        if not graph.system.name:
            self._issue(Severity.ERROR, "System must have a name",
                       pass_name="structural")

        # Check for no modules
        if not graph.system.modules:
            self._issue(Severity.WARNING, "System has no modules defined",
                       pass_name="structural")

        # Check for duplicate module names
        mod_names = [m.name for m in graph.system.modules]
        if len(mod_names) != len(set(mod_names)):
            seen = set()
            for name in mod_names:
                if name in seen:
                    self._issue(Severity.ERROR, f"Duplicate module name: {name}",
                               pass_name="structural")
                seen.add(name)

        # Check dependency acyclicity
        dep_graph = graph.get_dependency_graph()
        if dep_graph.has_cycle():
            self._issue(Severity.ERROR,
                       "Dependency graph contains a cycle — this is only "
                       "permitted if explicitly annotated as an intentional "
                       "bounded-context coupling",
                       pass_name="structural")

        # Check for orphaned nodes (nodes with no parents)
        all_node_ids = set(graph.nodes.keys())
        parented_ids = set()
        for edge in graph.edges:
            if edge.edge_type == EdgeType.OWNS:
                parented_ids.add(edge.target_id)
        orphaned = all_node_ids - parented_ids
        # Root system node is allowed to be "orphaned" by design
        orphaned = {n for n in orphaned if not n.startswith("system:")}
        for node_id in orphaned:
            self._issue(Severity.WARNING, f"Orphaned node: {node_id}",
                       node_id=node_id, pass_name="structural")

    # ─── Pass 2: Type Validation ───

    def _pass_type_validation(self, graph: ISRGraph):
        """Validate edge-node compatibility per the type rules."""
        for idx, edge in enumerate(graph.edges):
            source = graph.get_node(edge.source_id)
            target = graph.get_node(edge.target_id)

            if not source or not target:
                continue  # Will be caught by reference resolution

            rules = self._TYPE_RULES.get(edge.edge_type, {})
            valid_targets = rules.get(source.node_type, [])

            if not valid_targets:
                # Edge type not defined for this source type
                self._issue(Severity.ERROR,
                           f"Type error: {source.node_type.value} cannot have "
                           f"'{edge.edge_type.value}' edges",
                           node_id=source.node_id, edge_index=idx,
                           pass_name="type_validation")
                continue

            if target.node_type not in valid_targets:
                self._issue(Severity.ERROR,
                           f"Type error: {source.node_type.value} --[{edge.edge_type.value}]--> "
                           f"{target.node_type.value} is not a valid combination",
                           node_id=source.node_id, edge_index=idx,
                           pass_name="type_validation",
                           details={
                               "source_type": source.node_type.value,
                               "edge_type": edge.edge_type.value,
                               "target_type": target.node_type.value,
                               "expected_targets": [t.value for t in valid_targets],
                           })

    # ─── Pass 3: Reference Resolution ───

    def _pass_reference_resolution(self, graph: ISRGraph):
        """Ensure all identifiers resolve to existing nodes."""
        for idx, edge in enumerate(graph.edges):
            if edge.source_id not in graph.nodes:
                self._issue(Severity.ERROR,
                           f"Unresolved source reference: {edge.source_id}",
                           edge_index=idx, pass_name="reference_resolution")
            if edge.target_id not in graph.nodes:
                self._issue(Severity.ERROR,
                           f"Unresolved target reference: {edge.target_id}",
                           edge_index=idx, pass_name="reference_resolution")

        # Check entity relationships
        for node in graph.get_nodes_by_type(NodeType.MODULE):
            module = node.data
            for entity in module.entities:
                for rel in entity.relationships:
                    target_mod = rel.target_module or module.name
                    target_id = f"entity:{target_mod}:{rel.target_entity}"
                    if target_id not in graph.nodes:
                        self._issue(Severity.ERROR,
                                   f"Entity relationship target not found: "
                                   f"{rel.target_entity} in module {target_mod}",
                                   node_id=node.node_id,
                                   pass_name="reference_resolution")

        # Check service dependencies
        for node in graph.get_nodes_by_type(NodeType.SERVICE):
            service = node.data
            for dep in service.dependencies:
                target_mod = dep.target_module or node.module_name
                dep_id = f"service:{target_mod}:{dep.target_service}"
                if dep_id not in graph.nodes:
                    self._issue(Severity.WARNING,
                               f"Service dependency target not found: "
                               f"{dep.target_service} in module {target_mod}",
                               node_id=node.node_id,
                               pass_name="reference_resolution")

    # ─── Pass 4: Reachability Analysis ───

    def _pass_reachability(self, graph: ISRGraph):
        """Ensure all workflow states are reachable and no orphaned nodes."""
        for wf_node in graph.get_nodes_by_type(NodeType.WORKFLOW):
            workflow = wf_node.data
            if not workflow.states:
                self._issue(Severity.WARNING,
                           f"Workflow '{workflow.name}' has no states defined",
                           node_id=wf_node.node_id, pass_name="reachability")
                continue

            initial_states = [s for s in workflow.states if s.is_initial]
            if not initial_states:
                self._issue(Severity.ERROR,
                           f"Workflow '{workflow.name}' has no initial state",
                           node_id=wf_node.node_id, pass_name="reachability")

            # Build reachability map from transitions
            transition_map: Dict[str, List[str]] = {}
            for t in workflow.transitions:
                if t.from_state not in transition_map:
                    transition_map[t.from_state] = []
                transition_map[t.from_state].append(t.to_state)

            # BFS from initial states
            reachable = set()
            stack = [s.name for s in initial_states]
            while stack:
                state = stack.pop()
                if state in reachable:
                    continue
                reachable.add(state)
                for next_state in transition_map.get(state, []):
                    stack.append(next_state)

            # Check all states reachable
            for state in workflow.states:
                if state.name not in reachable and not state.is_initial:
                    self._issue(Severity.WARNING,
                               f"Workflow state '{state.name}' is not reachable "
                               f"in workflow '{workflow.name}'",
                               node_id=wf_node.node_id,
                               pass_name="reachability")

    # ─── Pass 5: Permission Consistency ───

    def _pass_permission_consistency(self, graph: ISRGraph):
        """Ensure all referenced permissions are defined in policies."""
        # Collect all policy names by module
        policy_names: Dict[str, Set[str]] = {}
        for node in graph.get_nodes_by_type(NodeType.POLICY):
            mod = node.module_name or ""
            if mod not in policy_names:
                policy_names[mod] = set()
            policy_names[mod].add(node.data.name)

        # Check all security bindings reference existing policies
        for iface_node in graph.get_nodes_by_type(NodeType.INTERFACE):
            iface = iface_node.data
            for binding in iface.security_bindings:
                mod = iface_node.module_name or ""
                mod_policies = policy_names.get(mod, set())
                if binding.policy_name not in mod_policies:
                    # Check system-wide policies
                    system_policies = policy_names.get("", set())
                    if binding.policy_name not in system_policies:
                        self._issue(Severity.ERROR,
                                   f"Interface '{iface.name}' references undefined "
                                   f"policy '{binding.policy_name}' in module '{mod}'",
                                   node_id=iface_node.node_id,
                                   pass_name="permission_consistency")

    # ─── Pass 6: Dependency Satisfaction ───

    def _pass_dependency_satisfaction(self, graph: ISRGraph):
        """Ensure all declared dependencies exist and are accessible."""
        for svc_node in graph.get_nodes_by_type(NodeType.SERVICE):
            service = svc_node.data

            # Check that events emitted are defined in the module
            mod = svc_node.module_name or ""
            for event_name in service.events:
                event_id = f"event:{mod}:{event_name}"
                if event_id not in graph.nodes:
                    self._issue(Severity.WARNING,
                               f"Service '{service.name}' emits event "
                               f"'{event_name}' which is not defined in "
                               f"module '{mod}'",
                               node_id=svc_node.node_id,
                               pass_name="dependency_satisfaction")

            # Check that consumed events exist
            for event_name in service.consumes:
                found = False
                for mod_node in graph.get_nodes_by_type(NodeType.MODULE):
                    evt_id = f"event:{mod_node.module_name}:{event_name}"
                    if evt_id in graph.nodes:
                        found = True
                        break
                if not found:
                    self._issue(Severity.WARNING,
                               f"Service '{service.name}' consumes event "
                               f"'{event_name}' which is not defined anywhere",
                               node_id=svc_node.node_id,
                               pass_name="dependency_satisfaction")

    # ─── Pass 7: Completeness Check ───

    def _pass_completeness(self, graph: ISRGraph,
                           minimum_level: CompletenessLevel) -> CompletenessLevel:
        """Check if ISR meets the minimum completeness level."""
        actual = graph.compute_completeness_level()

        if actual.value < minimum_level.value:
            self._issue(Severity.ERROR,
                       f"ISR completeness level {actual.name} is below "
                       f"required minimum {minimum_level.name}",
                       pass_name="completeness")

        return actual

    # ─── Convenience Validators ───

    def validate_for_compilation(self, graph: ISRGraph) -> ValidationResult:
        """Validate that an ISR is ready for compilation (L2 minimum)."""
        return self.validate(graph, minimum_level=CompletenessLevel.L2_BEHAVIOURAL)

    def validate_for_deployment(self, graph: ISRGraph) -> ValidationResult:
        """Validate that an ISR is ready for deployment (L4 minimum)."""
        return self.validate(graph, minimum_level=CompletenessLevel.L4_INFRASTRUCTURE)