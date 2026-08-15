"""
ISR Serializer — Converts ISR graphs to JSON for persistence and transport.

The serialization format is designed for:
- Lossless round-trip (JSON ↔ in-memory graph)
- Human readability
- Diffability (JSON diff tools work naturally)
- Schema validation (JSON Schema)
"""

from __future__ import annotations

import json
from typing import Dict, List, Optional, Any, Type
from dataclasses import is_dataclass, fields

from constitutional_architecture.isr.legacy_model import (
    System, Module, Entity, Service, Workflow, Policy,
    Interface, Event, Deployment, Constraint,
    Field, Operation, State, Transition, Action,
    Rule, Permission, Endpoint, Contract, SecurityBinding,
    Relationship, Dependency, Scaling, Networking, Storage,
    Secrets, Monitoring, Metadata,
    NodeType, EdgeType, Cardinality, CompletenessLevel, Severity,
)
from constitutional_architecture.isr.isr_graph import ISRGraph, ISRNode, ISREdge


class ISRSerializer:
    """Serializes ISR graphs to JSON."""

    def serialize_system(self, system: System) -> dict:
        """Serialize a System to a JSON-compatible dict."""
        return self._serialize_dataclass(system)

    def serialize_graph(self, graph: ISRGraph) -> dict:
        """Serialize an ISRGraph to a JSON-compatible dict."""
        return {
            "system": self.serialize_system(graph.system),
            "graph": {
                "nodes": {
                    nid: {
                        "node_id": node.node_id,
                        "node_type": node.node_type.value,
                        "module_name": node.module_name,
                        "parent_id": node.parent_id,
                        "attributes": node.attributes,
                    }
                    for nid, node in graph.nodes.items()
                },
                "edges": [
                    {
                        "source_id": e.source_id,
                        "target_id": e.target_id,
                        "edge_type": e.edge_type.value,
                        "cardinality": getattr(e.cardinality, 'value', e.cardinality),
                        "attributes": e.attributes,
                    }
                    for e in graph.edges
                ],
            },
        }

    def to_json(self, graph: ISRGraph, indent: int = 2) -> str:
        """Serialize an ISRGraph to a JSON string."""
        return json.dumps(self.serialize_graph(graph), indent=indent, default=str)

    def to_json_file(self, graph: ISRGraph, filepath: str, indent: int = 2):
        """Serialize an ISRGraph to a JSON file."""
        with open(filepath, 'w') as f:
            json.dump(self.serialize_graph(graph), f, indent=indent, default=str)

    def _serialize_dataclass(self, obj: Any) -> Any:
        """Recursively serialize a dataclass to a dict."""
        if obj is None:
            return None
        if isinstance(obj, (str, int, float, bool)):
            return obj
        if isinstance(obj, Enum):
            return obj.value
        if isinstance(obj, (list, tuple)):
            return [self._serialize_dataclass(item) for item in obj]
        if isinstance(obj, dict):
            return {k: self._serialize_dataclass(v) for k, v in obj.items()}

        if is_dataclass(obj):
            result = {}
            for f in fields(obj):
                value = getattr(obj, f.name)
                if value != f.default and value != f.default_factory:
                    result[f.name] = self._serialize_dataclass(value)
            # Add type discriminator
            if hasattr(obj, 'node_type'):
                result['_type'] = obj.node_type.value
            return result

        return str(obj)