"""Versioned ISR schema registry, validation, and deterministic migrations.

The registry is the single executable authority for schema-version support.
Schema 1.x preserves the frozen D03 9-node/8-edge contract. Schema 2.0
formalizes the expanded 14-node/18-edge taxonomy under an explicit ADR.
"""
from __future__ import annotations

from dataclasses import dataclass
from uuid import NAMESPACE_URL, uuid5

from isr.core.graph import EDGE_TYPE_COMPATIBILITY, Edge, EdgeType, ISRGraph, Node, NodeType


class ISRSchemaViolation(ValueError):
    """Raised when a graph does not conform to its declared ISR schema."""


@dataclass(frozen=True)
class SchemaDefinition:
    version: str
    node_types: frozenset[str]
    edge_types: frozenset[str]
    edge_compatibility: dict[str, tuple[frozenset[str], frozenset[str]]]


_V1_NODES = frozenset({
    "domain", "capability", "service", "api", "data_model", "event",
    "security_policy", "infrastructure_target", "requirement_ref",
})
_V1_EDGES = frozenset({
    "satisfies", "implemented_by", "exposes", "persists", "publishes",
    "consumed_by", "depends_on", "secured_by",
})
_V1_COMPATIBILITY = {
    "satisfies": (frozenset({"capability", "service"}), frozenset({"requirement_ref"})),
    "implemented_by": (frozenset({"capability"}), frozenset({"service"})),
    "exposes": (frozenset({"service"}), frozenset({"api"})),
    "persists": (frozenset({"service", "api"}), frozenset({"data_model"})),
    "publishes": (frozenset({"service"}), frozenset({"event"})),
    "consumed_by": (frozenset({"event"}), frozenset({"service", "api"})),
    "depends_on": (frozenset(_V1_NODES), frozenset(_V1_NODES)),
    "secured_by": (frozenset(_V1_NODES - {"security_policy"}), frozenset({"security_policy"})),
}
_V2_NODES = frozenset(item.value for item in NodeType)
_V2_EDGES = frozenset(item.value for item in EdgeType)
_V2_COMPATIBILITY = {
    edge.value: (frozenset(node.value for node in sources),
                 frozenset(node.value for node in targets))
    for edge, (sources, targets) in EDGE_TYPE_COMPATIBILITY.items()
}

SCHEMA_REGISTRY: dict[str, SchemaDefinition] = {
    "1.0": SchemaDefinition("1.0", _V1_NODES, _V1_EDGES, _V1_COMPATIBILITY),
    "1.1": SchemaDefinition("1.1", _V1_NODES, _V1_EDGES, _V1_COMPATIBILITY),
    "2.0": SchemaDefinition("2.0", _V2_NODES, _V2_EDGES, _V2_COMPATIBILITY),
}
CURRENT_SCHEMA_VERSION = "2.0"
LATEST_MIGRATION = ("1.1", "2.0")
SUPPORTED_SCHEMA_VERSIONS = tuple(SCHEMA_REGISTRY)


def validate_schema_graph(graph: ISRGraph, schema_version: str) -> None:
    """Validate taxonomy and endpoint compatibility for the declared version."""
    definition = SCHEMA_REGISTRY.get(schema_version)
    if definition is None:
        raise ISRSchemaViolation(
            f"Unsupported ISR schema version {schema_version!r}; "
            f"supported versions: {', '.join(SUPPORTED_SCHEMA_VERSIONS)}"
        )
    for key, node in sorted(graph.nodes.items()):
        node_type = node.type.value
        if node_type not in definition.node_types:
            raise ISRSchemaViolation(
                f"Node {key!r} uses {node_type!r}, which is not valid in ISR "
                f"schema {schema_version}"
            )
    for key, edge in sorted(graph.edges.items()):
        if edge.source_id not in graph.nodes or edge.target_id not in graph.nodes:
            raise ISRSchemaViolation(
                f"Edge {key!r} has a missing endpoint in ISR schema {schema_version}"
            )
        edge_type = edge.type.value
        if edge_type not in definition.edge_types:
            raise ISRSchemaViolation(
                f"Edge {key!r} uses {edge_type!r}, which is not valid in ISR "
                f"schema {schema_version}"
            )
        compatibility = definition.edge_compatibility.get(edge_type)
        if compatibility is None:
            raise ISRSchemaViolation(
                f"Edge {key!r} has no endpoint compatibility rule in schema {schema_version}"
            )
        source_type = graph.nodes[edge.source_id].type.value
        target_type = graph.nodes[edge.target_id].type.value
        allowed_sources, allowed_targets = compatibility
        if source_type not in allowed_sources or target_type not in allowed_targets:
            raise ISRSchemaViolation(
                f"Edge {key!r} ({edge_type}) has endpoints "
                f"{source_type} -> {target_type}, invalid in schema {schema_version}"
            )


def _with_node_schema_version(graph: ISRGraph, version: str) -> ISRGraph:
    nodes = {}
    for key, node in sorted(graph.nodes.items()):
        properties = dict(node.properties)
        properties["schema_version"] = version
        nodes[key] = Node(id=node.id, type=node.type, properties=properties)
    edges = {key: edge for key, edge in sorted(graph.edges.items())}
    return ISRGraph(nodes=nodes, edges=edges)


def migrate_1_0_to_1_1(graph: ISRGraph) -> ISRGraph:
    """Pure deterministic migration from the frozen 1.0 contract to 1.1."""
    validate_schema_graph(graph, "1.0")
    migrated = _with_node_schema_version(graph, "1.1")
    validate_schema_graph(migrated, "1.1")
    return migrated


def migrate_1_1_to_2_0(graph: ISRGraph) -> ISRGraph:
    """Pure deterministic migration from the 1.1 contract to expanded 2.0.

    This migration preserves the graph exactly except for the version marker.
    It does not invent frontend/effect/requirement relationships. New 2.0
    semantics must be introduced by an explicitly reviewed transformation.
    """
    validate_schema_graph(graph, "1.1")
    migrated = _with_node_schema_version(graph, "2.0")
    validate_schema_graph(migrated, "2.0")
    return migrated


def migrate_graph(graph: ISRGraph, source_version: str, target_version: str) -> ISRGraph:
    """Migrate only along registered, explicit migration edges."""
    if source_version not in SCHEMA_REGISTRY or target_version not in SCHEMA_REGISTRY:
        raise ISRSchemaViolation(
            f"Unsupported migration {source_version!r} -> {target_version!r}"
        )
    if source_version == target_version:
        validate_schema_graph(graph, source_version)
        return graph
    if (source_version, target_version) == ("1.0", "1.1"):
        return migrate_1_0_to_1_1(graph)
    if (source_version, target_version) == ("1.1", "2.0"):
        return migrate_1_1_to_2_0(graph)
    if (source_version, target_version) == ("1.0", "2.0"):
        return migrate_1_1_to_2_0(migrate_1_0_to_1_1(graph))
    raise ISRSchemaViolation(
        f"No registered deterministic migration from {source_version} to {target_version}"
    )


def migrate_revision(
    revision,
    target_version: str,
    *,
    migration_id: str,
    created_at: str,
):
    """Create a new immutable revision with explicit parent and migration lineage."""
    if not migration_id.strip():
        raise ValueError("migration_id must be non-empty")
    migrated_graph = migrate_graph(revision.graph, revision.schema_version, target_version)
    from isr.core.identity import Provenance, compute_content_hash, compute_revision_hash
    from isr.core.revision import ISRRevision

    graph_hash = compute_content_hash(target_version, migrated_graph)
    provenance = Provenance(
        parent_revision_id=revision.revision_id,
        requirement_refs=list(revision.provenance.requirement_refs),
        derivation_refs=[
            *revision.provenance.derivation_refs,
            f"migration:{migration_id}",
            f"source_revision:{revision.revision_id}",
            f"source_content_hash:{revision.content_hash}",
            f"source_revision_hash:{revision.revision_hash}",
        ],
        created_by=f"migration:{migration_id}",
        created_at=created_at,
    )
    revision_envelope_hash = compute_revision_hash(
        revision.system_id, target_version, graph_hash, provenance
    )
    new_revision_id = str(uuid5(
        NAMESPACE_URL, f"esap:isr:{revision.system_id}:{revision_envelope_hash}"
    ))
    return ISRRevision.create(
        system_id=revision.system_id,
        revision_id=new_revision_id,
        schema_version=target_version,
        graph=migrated_graph,
        provenance=provenance,
    )
