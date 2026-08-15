"""
Deployment View.

Projects the ISR graph into an infrastructure-focused view
consumed by the Infrastructure Engineer agent.
"""

from __future__ import annotations

from dataclasses import dataclass

from constitutional_architecture.isr.graph.typed_graph import TypedGraph
from constitutional_architecture.isr.model.nodes import NodeType


@dataclass(frozen=True)
class DeploymentView:
    """The deployment view of the ISR."""

    deployment_nodes: tuple[dict, ...] = ()
    services_with_deployment: tuple[str, ...] = ()
    services_without_deployment: tuple[str, ...] = ()
    has_monitoring: bool = False
    has_scaling: bool = False
    has_secrets_management: bool = False


class DeploymentViewBuilder:
    """Builds the deployment view from an ISR graph."""

    @staticmethod
    def build(graph: TypedGraph) -> DeploymentView:
        deployments = graph.get_nodes_by_type(NodeType.DEPLOYMENT)
        services = graph.get_nodes_by_type(NodeType.SERVICE)

        deployment_nodes = tuple(
            {"id": d.id, "label": d.label, "attributes": d.attributes}
            for d in deployments
        )

        from constitutional_architecture.isr.model.edges import EdgeType
        deployed_services: set[str] = set()
        for edge in graph.get_edges_by_type(EdgeType.DEPLOYS_TO):
            deployed_services.add(edge.source_id)

        with_deploy = tuple(s.id for s in services if s.id in deployed_services)
        without_deploy = tuple(s.id for s in services if s.id not in deployed_services)

        return DeploymentView(
            deployment_nodes=deployment_nodes,
            services_with_deployment=with_deploy,
            services_without_deployment=without_deploy,
            has_monitoring=len(deployments) > 0,
            has_scaling=len(deployments) > 0,
            has_secrets_management=len(deployments) > 0,
        )
