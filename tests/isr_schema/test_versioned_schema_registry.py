"""Versioned ISR schema enforcement and migration tests."""
from __future__ import annotations

import pytest

from isr.core.graph import ISRGraph, Node, NodeType
from isr.core.identity import Provenance
from isr.core.revision import ISRRevision
from isr.schema import (
    CURRENT_SCHEMA_VERSION,
    SCHEMA_REGISTRY,
    ISRSchemaViolation,
    migrate_graph,
    migrate_revision,
    validate_schema_graph,
)


def _provenance():
    return Provenance(created_by="schema-test", created_at="2026-11-05T00:00:00Z")


def _legacy_graph():
    return ISRGraph(nodes={
        "service": Node(id="service", type=NodeType.SERVICE, properties={"label": "billing"})
    }, edges={})


def _expanded_graph():
    return ISRGraph(nodes={
        "route": Node(id="route", type=NodeType.FRONTEND_ROUTE, properties={"label": "billing"})
    }, edges={})


def test_registry_has_one_current_version_and_explicit_historical_versions():
    assert CURRENT_SCHEMA_VERSION == "2.0"
    assert set(SCHEMA_REGISTRY) == {"1.0", "1.1", "2.0"}


@pytest.mark.parametrize("version", ["", "3.0", "1.2", "2"])
def test_unknown_schema_versions_fail_closed(version):
    with pytest.raises((ISRSchemaViolation, ValueError)):
        ISRRevision.create("sys", "rev", version, _legacy_graph(), _provenance())


@pytest.mark.parametrize("version", ["1.0", "1.1"])
def test_expanded_taxonomy_is_rejected_under_historical_schema(version):
    with pytest.raises(ISRSchemaViolation, match="not valid"):
        ISRRevision.create("sys", "rev", version, _expanded_graph(), _provenance())


def test_expanded_taxonomy_is_accepted_under_schema_2():
    revision = ISRRevision.create(
        "sys", "rev-2", "2.0", _expanded_graph(), _provenance()
    )
    assert revision.schema_version == "2.0"


def test_legacy_graph_migrates_deterministically_to_2_0_without_source_mutation():
    source = _legacy_graph()
    before = source.model_dump(mode="json")
    first = migrate_graph(source, "1.0", "2.0")
    second = migrate_graph(source, "1.0", "2.0")
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert source.model_dump(mode="json") == before
    assert first.nodes["service"].properties["schema_version"] == "2.0"


def test_revision_migration_creates_new_identity_and_parent_lineage():
    source = ISRRevision.create("sys", "rev-1", "1.0", _legacy_graph(), _provenance())
    migrated = migrate_revision(
        source,
        "2.0",
        migration_id="fs00-isr-v1-to-v2",
        created_at="2026-11-05T00:00:00Z",
    )
    assert migrated.schema_version == "2.0"
    assert migrated.revision_id != source.revision_id
    assert migrated.content_hash != source.content_hash
    assert migrated.provenance.parent_revision_id == source.revision_id
    assert f"source_content_hash:{source.content_hash}" in migrated.provenance.derivation_refs
    assert f"source_revision_hash:{source.revision_hash}" in migrated.provenance.derivation_refs
    assert "migration:fs00-isr-v1-to-v2" in migrated.provenance.derivation_refs


def test_schema_package_reexports_single_registry_implementation():
    from isr.schema import versions
    assert SCHEMA_REGISTRY is versions.SCHEMA_REGISTRY
    validate_schema_graph(_legacy_graph(), "1.0")



def test_graph_hash_and_revision_envelope_hash_have_distinct_meanings():
    first = ISRRevision.create(
        "sys", "rev-a", "2.0", _legacy_graph(),
        Provenance(created_by="author-a", created_at="2026-11-05T00:00:00Z"),
    )
    second = ISRRevision.create(
        "sys", "rev-b", "2.0", _legacy_graph(),
        Provenance(created_by="author-b", created_at="2026-11-05T00:00:00Z"),
    )
    assert first.content_hash == second.content_hash
    assert first.revision_hash != second.revision_hash
