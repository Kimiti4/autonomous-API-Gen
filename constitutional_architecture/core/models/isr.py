from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List

from pydantic import BaseModel, Field


class NodeType(str, Enum):
    DOMAIN = "Domain"
    DATA_ENTITY = "DataEntity"
    DATA_ATTRIBUTE = "DataAttribute"
    CAPABILITY = "Capability"
    SERVICE = "Service"
    COMPONENT = "Component"
    API_ENDPOINT = "APIEndpoint"
    EVENT = "Event"
    FRONTEND_VIEW = "FrontendView"
    SECURITY_POLICY = "SecurityPolicy"
    TENANCY_POLICY = "TenancyPolicy"
    RETENTION_POLICY = "RetentionPolicy"
    AUDIT_POLICY = "AuditPolicy"
    INFRA_REQUIREMENT = "InfraRequirement"
    OPERATIONAL_POLICY = "OperationalPolicy"
    SLO_DEFINITION = "SLODefinition"
    TELEMETRY_REQUIREMENT = "TelemetryRequirement"


class EdgeType(str, Enum):
    OWNS = "owns"
    IMPLEMENTS = "implements"
    EXPOSES = "exposes"
    EMITS = "emits"
    CONSUMES = "consumes"
    DEPENDS_ON = "depends_on"
    SECURES = "secures"
    PERSISTS = "persists"
    RENDERS = "renders"
    HAS_ATTRIBUTE = "has_attribute"
    RELATES_TO = "relates_to"
    GOVERNED_BY = "governed_by"
    MONITORS = "monitors"


class ISRNode(BaseModel):
    id: str
    type: NodeType
    semantic_attributes: Dict[str, Any] = Field(default_factory=dict)


class ISREdge(BaseModel):
    source_id: str
    target_id: str
    type: EdgeType
    attributes: Dict[str, Any] = Field(default_factory=dict)


class UniversalISR(BaseModel):
    version: str = "1.0.0"
    intent_hash: str = ""
    genome_hash: str = ""

    nodes: Dict[str, ISRNode] = Field(default_factory=dict)
    edges: List[ISREdge] = Field(default_factory=list)

    def add_node(self, node: ISRNode) -> None:
        if node.id in self.nodes:
            raise ValueError(f"Node {node.id} already exists.")
        self.nodes[node.id] = node

    def add_edge(self, edge: ISREdge) -> None:
        if edge.source_id not in self.nodes or edge.target_id not in self.nodes:
            raise ValueError("Edge references non-existent nodes.")
        self.edges.append(edge)

    def get_nodes_by_type(self, node_type: NodeType) -> List[ISRNode]:
        return [n for n in self.nodes.values() if n.type == node_type]

    def get_edges_by_type(self, edge_type: EdgeType) -> List[ISREdge]:
        return [e for e in self.edges if e.type == edge_type]

    def has_cycle(self) -> bool:
        visited: set[str] = set()
        rec_stack: set[str] = set()

        def dfs(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)
            for edge in self.edges:
                if edge.source_id == node_id:
                    target = edge.target_id
                    if target not in visited:
                        if dfs(target):
                            return True
                    elif target in rec_stack:
                        return True
            rec_stack.discard(node_id)
            return False

        for node_id in self.nodes:
            if node_id not in visited:
                if dfs(node_id):
                    return True
        return False
