"""
Contract tests for Knowledge Graph plugins.

Any graph store or search store plugin should pass these contract tests
before being accepted into a deployment.
"""

from __future__ import annotations

from ..models import (
    Entity,
    EntityCreate,
    Relation,
    RelationCreate,
    SearchRequest,
    SourceRef,
    utcnow,
)


def _source_ref() -> SourceRef:
    return SourceRef(
        source_type="PLUGIN_CONTRACT_TEST",
        source_id="contract_test_source",
        source_hash="sha256:contract_test",
    )


def _make_entity(
    name: str,
    entity_type: str = "SERVICE",
    namespace: str = "plugin_contract",
) -> Entity:
    data = EntityCreate(
        entity_type=entity_type,
        name=name,
        namespace=namespace,
        description="Entity created by plugin contract tests.",
        source_refs=[_source_ref()],
    )

    return Entity(
        **data.model_dump(),
        id=data.compute_id(),
        content_hash=data.compute_content_hash(),
        created_at=utcnow(),
    )


def _make_relation(
    source_entity_id: str,
    target_entity_id: str,
    relation_type: str = "DEPENDS_ON",
) -> Relation:
    data = RelationCreate(
        relation_type=relation_type,
        source_entity_id=source_entity_id,
        target_entity_id=target_entity_id,
        source_refs=[_source_ref()],
    )

    return Relation(
        **data.model_dump(),
        id=data.compute_id(),
        content_hash=data.compute_content_hash(),
        created_at=utcnow(),
    )


def run_graph_store_contract_tests(graph_store) -> None:
    """
    Run required contract tests against a graph store plugin.

    The graph store must implement:
    - upsert_entity
    - get_entity
    - list_entities
    - upsert_relation
    - get_relation
    - neighbors
    - find_paths
    """

    service = _make_entity("ContractService")
    dependency = _make_entity("ContractDependency")

    graph_store.upsert_entity(service)
    graph_store.upsert_entity(dependency)

    fetched_service = graph_store.get_entity(service.id)

    assert fetched_service is not None
    assert fetched_service.name == "ContractService"

    entities = graph_store.list_entities(entity_type="SERVICE")

    assert any(entity.id == service.id for entity in entities)

    relation = _make_relation(
        source_entity_id=service.id,
        target_entity_id=dependency.id,
    )

    graph_store.upsert_relation(relation)

    fetched_relation = graph_store.get_relation(relation.id)

    assert fetched_relation is not None
    assert fetched_relation.source_entity_id == service.id
    assert fetched_relation.target_entity_id == dependency.id

    graph_slice = graph_store.neighbors(
        entity_id=service.id,
        direction="both",
        relation_types=[],
        depth=1,
    )

    neighbor_ids = {node.id for node in graph_slice.nodes}

    assert dependency.id in neighbor_ids

    paths = graph_store.find_paths(
        source_entity_id=service.id,
        target_entity_id=dependency.id,
        relation_types=[],
        depth=2,
        max_results=5,
    )

    assert len(paths) >= 1


def run_search_store_contract_tests(search_store) -> None:
    """
    Run required contract tests against a search store plugin.

    The search store must implement:
    - index_entity
    - search
    """

    entity = _make_entity("SearchableContractService")

    search_store.index_entity(entity)

    response = search_store.search(
        SearchRequest(
            text="SearchableContractService",
            entity_types=["SERVICE"],
            limit=10,
        )
    )

    assert any(result.entity_id == entity.id for result in response.results)