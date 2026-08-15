"""
Static Fitness Evaluator.

Computes fitness metrics directly from the ISR graph without executing code.
This is the fast fitness tier used during evolution to prune candidates.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from constitutional_architecture.isr.graph.typed_graph import TypedGraph
from constitutional_architecture.isr.metrics.complexity import ComplexityMetrics
from constitutional_architecture.isr.metrics.coupling import CouplingMetrics
from constitutional_architecture.isr.metrics.cohesion import CohesionMetrics
from constitutional_architecture.isr.model.edges import EdgeType
from constitutional_architecture.isr.model.nodes import NodeType


@dataclass(frozen=True)
class FitnessVector:
    """Multi-dimensional fitness vector for an ISR."""

    complexity: float = 0.0
    coupling: float = 0.0
    cohesion: float = 0.0
    security_coverage: float = 0.0
    scalability: float = 0.0
    reliability: float = 0.0
    deployment_completeness: float = 0.0
    observability: float = 0.0
    documentation: float = 0.0
    maintainability: float = 0.0
    extensibility: float = 0.0
    architecture_quality: float = 0.0

    def to_dict(self) -> dict[str, float]:
        return {
            "complexity": self.complexity,
            "coupling": self.coupling,
            "cohesion": self.cohesion,
            "security_coverage": self.security_coverage,
            "scalability": self.scalability,
            "reliability": self.reliability,
            "deployment_completeness": self.deployment_completeness,
            "observability": self.observability,
            "documentation": self.documentation,
            "maintainability": self.maintainability,
            "extensibility": self.extensibility,
            "architecture_quality": self.architecture_quality,
        }

    @property
    def dimensions(self) -> int:
        return 12

    def composite_score(self, weights: dict[str, float] | None = None) -> float:
        if weights is None:
            weights = {k: 1.0 / 12.0 for k in self.to_dict()}
        total = sum(self.to_dict().get(k, 0.0) * w for k, w in weights.items())
        return total / sum(weights.values()) if weights else 0.0


class StaticFitnessEvaluator:
    """
    Evaluates fitness directly from ISR graph properties.

    Does NOT execute code. Does NOT require compilation.
    Used during evolution for fast candidate pruning.
    """

    def evaluate(self, graph: TypedGraph) -> FitnessVector:
        return FitnessVector(
            complexity=self._evaluate_complexity(graph),
            coupling=self._evaluate_coupling(graph),
            cohesion=self._evaluate_cohesion(graph),
            security_coverage=self._evaluate_security(graph),
            scalability=self._evaluate_scalability(graph),
            reliability=self._evaluate_reliability(graph),
            deployment_completeness=self._evaluate_deployment(graph),
            observability=self._evaluate_observability(graph),
            documentation=self._evaluate_documentation(graph),
            maintainability=self._evaluate_maintainability(graph),
            extensibility=self._evaluate_extensibility(graph),
            architecture_quality=self._evaluate_architecture_quality(graph),
        )

    def _evaluate_complexity(self, graph: TypedGraph) -> float:
        raw = ComplexityMetrics.compute_complexity_score(graph)
        return 1.0 - raw

    def _evaluate_coupling(self, graph: TypedGraph) -> float:
        raw = CouplingMetrics.compute_coupling_score(graph)
        return 1.0 - raw

    def _evaluate_cohesion(self, graph: TypedGraph) -> float:
        return CohesionMetrics.compute_cohesion_score(graph)

    def _evaluate_security(self, graph: TypedGraph) -> float:
        interfaces = graph.get_nodes_by_type(NodeType.INTERFACE)
        if not interfaces:
            return 0.5

        secured = 0
        for iface in interfaces:
            has_policy = any(
                e.edge_type == EdgeType.SECURED_BY
                for e in graph.get_outgoing_edges(iface.id)
            )
            if has_policy:
                secured += 1

        return secured / len(interfaces)

    def _evaluate_scalability(self, graph: TypedGraph) -> float:
        services = graph.get_nodes_by_type(NodeType.SERVICE)
        if not services:
            return 0.5

        stateless = sum(
            1 for s in services
            if s.attributes.get("is_stateless", True)
        )
        return stateless / len(services)

    def _evaluate_reliability(self, graph: TypedGraph) -> float:
        events = graph.get_nodes_by_type(NodeType.EVENT)
        services = graph.get_nodes_by_type(NodeType.SERVICE)
        if not services:
            return 0.5

        event_ratio = min(len(events) / max(len(services), 1), 1.0)
        return 0.5 + 0.5 * event_ratio

    def _evaluate_deployment(self, graph: TypedGraph) -> float:
        deployments = graph.get_nodes_by_type(NodeType.DEPLOYMENT)
        if not deployments:
            return 0.0
        return min(len(deployments) / 1.0, 1.0)

    def _evaluate_observability(self, graph: TypedGraph) -> float:
        deployments = graph.get_nodes_by_type(NodeType.DEPLOYMENT)
        if not deployments:
            return 0.3
        return 0.7

    def _evaluate_documentation(self, graph: TypedGraph) -> float:
        doc_nodes = graph.get_nodes_by_type(NodeType.DOCUMENTATION)
        modules = graph.get_nodes_by_type(NodeType.MODULE)
        if not modules:
            return 0.5
        return min(len(doc_nodes) / len(modules), 1.0)

    def _evaluate_maintainability(self, graph: TypedGraph) -> float:
        avg_size = ComplexityMetrics.average_module_size(graph)
        if 3 <= avg_size <= 7:
            return 1.0
        elif avg_size < 3:
            return 0.7
        else:
            return max(0.3, 1.0 - (avg_size - 7) * 0.1)

    def _evaluate_extensibility(self, graph: TypedGraph) -> float:
        interfaces = graph.get_nodes_by_type(NodeType.INTERFACE)
        services = graph.get_nodes_by_type(NodeType.SERVICE)
        if not services:
            return 0.5
        return min(len(interfaces) / len(services), 1.0)

    def _evaluate_architecture_quality(self, graph: TypedGraph) -> float:
        cohesion = self._evaluate_cohesion(graph)
        coupling = self._evaluate_coupling(graph)
        complexity = self._evaluate_complexity(graph)
        return (cohesion + coupling + complexity) / 3.0
