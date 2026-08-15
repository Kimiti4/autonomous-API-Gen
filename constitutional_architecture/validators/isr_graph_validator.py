from __future__ import annotations

import re
from typing import Set

from constitutional_architecture.core.governance import FORBIDDEN_LEXICON
from constitutional_architecture.core.models.isr import EdgeType, NodeType, UniversalISR


class ISRGraphViolation(Exception):
    pass


class ISRGraphValidator:
    def __init__(self, forbidden_lexicon: Set[str] = FORBIDDEN_LEXICON) -> None:
        self._forbidden = forbidden_lexicon

    def validate(self, isr: UniversalISR) -> None:
        self._check_technology_purity(isr)
        self._check_security_coverage(isr)
        self._check_orphaned_entities(isr)

    def _check_technology_purity(self, isr: UniversalISR) -> None:
        for node in isr.nodes.values():
            text = str(node.semantic_attributes).lower()
            for term in self._forbidden:
                if len(term) >= 4 and re.search(rf'\b{re.escape(term)}\b', text):
                    raise ISRGraphViolation(
                        f"ISR Node '{node.id}' contains forbidden technology '{term}'."
                    )

    def _check_security_coverage(self, isr: UniversalISR) -> None:
        secured_targets = {
            e.target_id for e in isr.edges if e.type == EdgeType.SECURES
        }

        for node_id, node in isr.nodes.items():
            if node.type in (NodeType.SERVICE, NodeType.API_ENDPOINT, NodeType.COMPONENT):
                if node_id not in secured_targets:
                    raise ISRGraphViolation(
                        f"Security by Design violated: {node.type.value} '{node_id}' has no SecurityPolicy applied."
                    )

    def _check_orphaned_entities(self, isr: UniversalISR) -> None:
        owned_entities = {
            e.target_id for e in isr.edges if e.type == EdgeType.OWNS
        }
        for node_id, node in isr.nodes.items():
            if node.type == NodeType.DATA_ENTITY and node_id not in owned_entities:
                raise ISRGraphViolation(
                    f"Domain-Driven Design violated: DataEntity '{node_id}' is not owned by any Domain."
                )
