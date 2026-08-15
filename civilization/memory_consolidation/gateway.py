"""
Knowledge Graph sync gateways.

The gateway abstraction keeps the memory consolidation engine independent of
a specific Knowledge Graph implementation.
"""

from __future__ import annotations

from typing import Dict, Protocol

from ..utils import deterministic_id, utcnow
from .models import KGEntityPayload, KGRelationPayload


class KnowledgeGraphGateway(Protocol):
    """Abstract Knowledge Graph gateway."""

    def upsert_entity(self, entity: KGEntityPayload) -> Dict:
        ...

    def upsert_relation(self, relation: KGRelationPayload) -> Dict:
        ...


class InMemoryKnowledgeGraphGateway:
    """In-memory Knowledge Graph gateway for tests and local development."""

    def __init__(self) -> None:
        self.entities: Dict[str, KGEntityPayload] = {}
        self.relations: Dict[str, KGRelationPayload] = {}

    def upsert_entity(self, entity: KGEntityPayload) -> Dict:
        entity_id = entity.id or deterministic_id(
            "kg_entity",
            {
                "entity_type": entity.entity_type,
                "namespace": entity.namespace,
                "name": entity.name,
            },
        )

        entity.id = entity_id

        self.entities[entity_id] = entity

        return {
            "id": entity_id,
            "status": "UPSERTED",
        }

    def upsert_relation(self, relation: KGRelationPayload) -> Dict:
        relation_id = relation.id or deterministic_id(
            "kg_relation",
            {
                "relation_type": relation.relation_type,
                "source_entity_id": relation.source_entity_id,
                "target_entity_id": relation.target_entity_id,
            },
        )

        relation.id = relation_id

        self.relations[relation_id] = relation

        return {
            "id": relation_id,
            "status": "UPSERTED",
        }
