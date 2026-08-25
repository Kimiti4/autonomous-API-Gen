"""ISR schema version registry and deterministic migration functions."""

from __future__ import annotations

from isr.core.graph import ISRGraph, Node

CURRENT_SCHEMA_VERSION = "1.1"
LATEST_MIGRATION = ("1.0", "1.1")


def migrate_1_0_to_1_1(graph: ISRGraph) -> ISRGraph:
    """Deterministic migration from ISR schema 1.0 → 1.1.

    1.1 adds a 'schema_version' property to every node for forward-compatible
    version tracking.  The migration is pure: identical input → identical output.
    """
    migrated_nodes = {}
    for key, node in sorted(graph.nodes.items()):
        new_props = dict(node.properties)
        new_props["schema_version"] = "1.1"
        migrated_nodes[key] = Node(
            id=node.id,
            type=node.type,
            properties=new_props,
        )

    migrated_edges = {}
    for key, edge in graph.edges.items():
        migrated_edges[key] = edge

    return ISRGraph(nodes=migrated_nodes, edges=migrated_edges)
