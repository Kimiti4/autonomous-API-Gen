from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List

from pydantic import BaseModel, Field


class NodeType(str, Enum):
    DOMAIN = "Domain"
    SERVICE = "Service"
    COMPONENT = "Component"
    API_ENDPOINT = "APIEndpoint"
    EVENT = "Event"
    DATA_ENTITY = "DataEntity"
    SECURITY_POLICY = "SecurityPolicy"
    INFRA_REQUIREMENT = "InfraRequirement"


class ISRNode(BaseModel):
    id: str
    type: NodeType
    attributes: Dict[str, Any] = Field(default_factory=dict)
    dependencies: List[str] = Field(default_factory=list)


class UniversalISR(BaseModel):
    version: str = "1.0.0"
    nodes: Dict[str, ISRNode] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def add_node(self, node: ISRNode) -> None:
        if node.id in self.nodes:
            raise ValueError(f"Node {node.id} already exists.")
        self.nodes[node.id] = node
