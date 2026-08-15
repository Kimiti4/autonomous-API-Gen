from __future__ import annotations

import re
from typing import Any, Dict, Set

from constitutional_architecture.core.models.universal_isr import ISRNode, NodeType, UniversalISR


FORBIDDEN_LEXICON: Set[str] = {
    "aws", "azure", "gcp", "kubernetes", "k8s", "docker",
    "terraform", "pulumi",
    "postgres", "postgresql", "mysql", "mongodb", "redis", "neo4j", "dynamodb",
    "react", "vue", "angular", "svelte", "fastapi", "django", "spring", "express",
    "node", "python", "go", "rust", "java", "c#",
}


class GovernanceRules:
    @staticmethod
    def is_technology_agnostic(attributes: Dict[str, Any]) -> bool:
        def scan_value(val: Any) -> bool:
            if isinstance(val, str):
                val_lower = val.lower()
                for term in FORBIDDEN_LEXICON:
                    if re.search(rf'\b{re.escape(term)}\b', val_lower):
                        return False
            elif isinstance(val, dict):
                return all(scan_value(v) for v in val.values())
            elif isinstance(val, list):
                return all(scan_value(v) for v in val)
            return True

        return all(scan_value(v) for v in attributes.values())

    @staticmethod
    def has_security_by_design(nodes: Dict[str, ISRNode]) -> bool:
        for node_id, node in nodes.items():
            if node.type in (NodeType.API_ENDPOINT, NodeType.SERVICE):
                has_sec_dep = any(
                    nodes[dep_id].type == NodeType.SECURITY_POLICY
                    for dep_id in node.dependencies
                    if dep_id in nodes
                )
                if not has_sec_dep:
                    return False
        return True

    @staticmethod
    def has_cycles(isr: UniversalISR) -> bool:
        visited: set[str] = set()
        rec_stack: set[str] = set()

        def dfs(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)
            for neighbor in isr.nodes[node_id].dependencies:
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            rec_stack.remove(node_id)
            return False

        for node_id in isr.nodes:
            if node_id not in visited:
                if dfs(node_id):
                    return True
        return False
