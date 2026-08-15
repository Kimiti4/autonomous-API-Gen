"""
Knowledge Graph storage abstraction.

The platform core must not depend on a specific graph database.

This module defines:
- GraphStore protocol
- InMemoryGraphStore reference implementation

Production deployments should replace InMemoryGraphStore with a persistent
SQL graph store or external graph-database adapter.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Optional, Protocol

from .errors import NotFound
from .models import Entity, GraphPath, GraphSlice, Relation


class GraphStore(Protocol):
    """Abstract graph storage adapter."""

    def upsert_entity(self, entity: Entity) -> Entity:
        ...

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        ...

    def list_entities(
        self,
        entity_type: Optional[str] = None,
        namespace: Optional[str] = None,
        limit: int = 100,
    ) -> list[Entity]:
        ...

    def upsert_relation(self, relation: Relation) -> Relation:
        ...

    def get_relation(self, relation_id: str) -> Optional[Relation]:
        ...

    def neighbors(
        self,
        entity_id: str,
        direction: str,
        relation_types: list[str],
        depth: int,
    ) -> GraphSlice:
        ...

    def find_paths(
        self,
        source_entity_id: str,
        target_entity_id: str,
        relation_types: list[str],
        depth: int,
        max_results: int,
    ) -> list[GraphPath]:
        ...


class InMemoryGraphStore:
    """
    In-memory graph store.

    This is a reference implementation for local development and tests.
    It is not intended to be the production persistence layer.
    """

    def __init__(self) -> None:
        self._entities: dict[str, Entity] = {}
        self._relations: dict[str, Relation] = {}
        self._outgoing: dict[str, set[str]] = defaultdict(set)
        self._incoming: dict[str, set[str]] = defaultdict(set)

    def upsert_entity(self, entity: Entity) -> Entity:
        self._entities[entity.id] = entity
        return entity

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        return self._entities.get(entity_id)

    def list_entities(
        self,
        entity_type: Optional[str] = None,
        namespace: Optional[str] = None,
        limit: int = 100,
    ) -> list[Entity]:
        results: list[Entity] = []

        for entity in self._entities.values():
            if entity_type and entity.entity_type != entity_type:
                continue
            if namespace and entity.namespace != namespace:
                continue

            results.append(entity)

            if len(results) >= limit:
                break

        return results

    def upsert_relation(self, relation: Relation) -> Relation:
        existing = self._relations.get(relation.id)

        if existing:
            self._outgoing[existing.source_entity_id].discard(relation.id)
            self._incoming[existing.target_entity_id].discard(relation.id)

        self._relations[relation.id] = relation
        self._outgoing[relation.source_entity_id].add(relation.id)
        self._incoming[relation.target_entity_id].add(relation.id)

        return relation

    def get_relation(self, relation_id: str) -> Optional[Relation]:
        return self._relations.get(relation_id)

    def neighbors(
        self,
        entity_id: str,
        direction: str,
        relation_types: list[str],
        depth: int,
    ) -> GraphSlice:
        if entity_id not in self._entities:
            raise NotFound(f"Entity not found: {entity_id}")

        visited_nodes: set[str] = {entity_id}
        visited_edges: set[str] = set()
        edges: list[Relation] = []
        frontier: list[str] = [entity_id]

        relation_filter = set(relation_types)

        for _ in range(depth):
            next_frontier: list[str] = []

            for node_id in frontier:
                relation_ids: set[str] = set()

                if direction in {"forward", "both"}:
                    relation_ids.update(self._outgoing.get(node_id, set()))

                if direction in {"backward", "both"}:
                    relation_ids.update(self._incoming.get(node_id, set()))

                for relation_id in relation_ids:
                    relation = self._relations.get(relation_id)

                    if not relation:
                        continue

                    if relation_filter and relation.relation_type not in relation_filter:
                        continue

                    if relation.source_entity_id == node_id:
                        neighbor_id = relation.target_entity_id
                    else:
                        neighbor_id = relation.source_entity_id

                    if relation_id not in visited_edges:
                        visited_edges.add(relation_id)
                        edges.append(relation)

                    if neighbor_id not in visited_nodes:
                        visited_nodes.add(neighbor_id)
                        next_frontier.append(neighbor_id)

            frontier = next_frontier

        nodes = [
            self._entities[node_id]
            for node_id in visited_nodes
            if node_id in self._entities
        ]

        return GraphSlice(nodes=nodes, edges=edges)

    def find_paths(
        self,
        source_entity_id: str,
        target_entity_id: str,
        relation_types: list[str],
        depth: int,
        max_results: int,
    ) -> list[GraphPath]:
        if source_entity_id not in self._entities:
            raise NotFound(f"Source entity not found: {source_entity_id}")

        if target_entity_id not in self._entities:
            raise NotFound(f"Target entity not found: {target_entity_id}")

        relation_filter = set(relation_types)
        results: list[GraphPath] = []

        queue: list[tuple[str, list[str], list[str]]] = [
            (source_entity_id, [source_entity_id], [])
        ]

        while queue:
            node_id, node_path, relation_path = queue.pop(0)

            if len(node_path) - 1 >= depth:
                continue

            for relation_id in self._outgoing.get(node_id, set()):
                relation = self._relations.get(relation_id)

                if not relation:
                    continue

                if relation_filter and relation.relation_type not in relation_filter:
                    continue

                next_node = relation.target_entity_id

                if next_node in node_path:
                    continue

                next_node_path = node_path + [next_node]
                next_relation_path = relation_path + [relation_id]

                if next_node == target_entity_id:
                    results.append(
                        GraphPath(
                            nodes=next_node_path,
                            relations=next_relation_path,
                        )
                    )

                    if len(results) >= max_results:
                        return results
                else:
                    queue.append((next_node, next_node_path, next_relation_path))

        return results
