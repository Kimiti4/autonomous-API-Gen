"""
Knowledge Graph runtime.

This is the core kernel that coordinates ontology validation, provenance,
storage, querying, tracing, and search.

It does not depend on a particular storage backend.
"""

from __future__ import annotations

from typing import Any, Optional, Union

from .errors import InvalidQuery, MissingProvenance, NotFound
from .models import (
    Entity,
    EntityCreate,
    QueryRequest,
    Relation,
    RelationCreate,
    SearchRequest,
    SearchResponse,
    utcnow,
)
from .ontology import validate_entity_type, validate_relation_type
from .search import SearchStore
from .store import GraphStore


class GraphRuntime:
    """
    Knowledge Graph runtime kernel.
    """

    def __init__(
        self,
        graph_store: GraphStore,
        search_store: SearchStore,
    ) -> None:
        self._graph_store = graph_store
        self._search_store = search_store

    def create_entity(
        self,
        data: EntityCreate,
        actor: str = "system",
    ) -> Entity:
        """
        Create or upsert a knowledge entity.

        Provenance is mandatory.
        """
        validate_entity_type(data.entity_type)

        if not data.source_refs:
            raise MissingProvenance("Entity creation requires source_refs.")

        content_hash = data.compute_content_hash()
        entity_id = data.compute_id()

        entity = Entity(
            **data.model_dump(),
            id=entity_id,
            content_hash=content_hash,
            created_at=utcnow(),
        )

        stored_entity = self._graph_store.upsert_entity(entity)
        self._search_store.index_entity(stored_entity)

        return stored_entity

    def get_entity(self, entity_id: str) -> Entity:
        entity = self._graph_store.get_entity(entity_id)

        if not entity:
            raise NotFound(f"Entity not found: {entity_id}")

        return entity

    def list_entities(
        self,
        entity_type: Optional[str] = None,
        namespace: Optional[str] = None,
        limit: int = 100,
    ) -> list[Entity]:
        return self._graph_store.list_entities(
            entity_type=entity_type,
            namespace=namespace,
            limit=limit,
        )

    def create_relation(
        self,
        data: RelationCreate,
        actor: str = "system",
    ) -> Relation:
        """
        Create or upsert a knowledge relation.

        Both endpoints must exist.
        Provenance is mandatory.
        """
        validate_relation_type(data.relation_type)

        if not data.source_refs:
            raise MissingProvenance("Relation creation requires source_refs.")

        source = self._graph_store.get_entity(data.source_entity_id)
        if not source:
            raise NotFound(f"Source entity not found: {data.source_entity_id}")

        target = self._graph_store.get_entity(data.target_entity_id)
        if not target:
            raise NotFound(f"Target entity not found: {data.target_entity_id}")

        content_hash = data.compute_content_hash()
        relation_id = data.compute_id()

        relation = Relation(
            **data.model_dump(),
            id=relation_id,
            content_hash=content_hash,
            created_at=utcnow(),
        )

        return self._graph_store.upsert_relation(relation)

    def get_relation(self, relation_id: str) -> Relation:
        relation = self._graph_store.get_relation(relation_id)

        if not relation:
            raise NotFound(f"Relation not found: {relation_id}")

        return relation

    def query(self, request: Union[QueryRequest, dict[str, Any]]) -> dict:
        """
        Execute a Knowledge Graph query.

        The query model is intentionally backend-neutral. A dict is coerced
        into a QueryRequest so callers may pass either form.
        """
        if isinstance(request, dict):
            request = QueryRequest(**request)

        if request.query_type == "ENTITY":
            if not request.entity_id:
                raise InvalidQuery("entity_id is required for ENTITY queries.")

            entity = self.get_entity(request.entity_id)
            return {
                "query_type": "ENTITY",
                "entity": entity.model_dump(mode="json"),
            }

        if request.query_type in {"NEIGHBORS", "TRACE", "IMPACT"}:
            if not request.entity_id:
                raise InvalidQuery(
                    f"entity_id is required for {request.query_type} queries."
                )

            graph_slice = self._graph_store.neighbors(
                entity_id=request.entity_id,
                direction=request.direction,
                relation_types=request.relation_types,
                depth=request.depth,
            )

            return {
                "query_type": request.query_type,
                "entity_id": request.entity_id,
                "direction": request.direction,
                "depth": request.depth,
                "nodes": [node.model_dump(mode="json") for node in graph_slice.nodes],
                "edges": [edge.model_dump(mode="json") for edge in graph_slice.edges],
            }

        if request.query_type == "PATH":
            if not request.source_entity_id or not request.target_entity_id:
                raise InvalidQuery(
                    "source_entity_id and target_entity_id are required for PATH queries."
                )

            paths = self._graph_store.find_paths(
                source_entity_id=request.source_entity_id,
                target_entity_id=request.target_entity_id,
                relation_types=request.relation_types,
                depth=request.depth,
                max_results=request.limit,
            )

            return {
                "query_type": "PATH",
                "source_entity_id": request.source_entity_id,
                "target_entity_id": request.target_entity_id,
                "paths": [path.model_dump(mode="json") for path in paths],
            }

        if request.query_type == "SEARCH":
            if not request.text:
                raise InvalidQuery("text is required for SEARCH queries.")

            response = self.search(
                SearchRequest(
                    text=request.text,
                    entity_types=request.entity_types,
                    limit=request.limit,
                )
            )

            return {
                "query_type": "SEARCH",
                "results": response.model_dump(mode="json")["results"],
            }

        raise InvalidQuery(f"Unsupported query type: {request.query_type}")

    def search(self, request: SearchRequest) -> SearchResponse:
        """
        Search knowledge entities.

        The search adapter enforces backend replaceability.
        """
        return self._search_store.search(request)
