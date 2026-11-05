"""The immutable, content-addressed ISR revision."""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from isr.core.behavior_validation import validate_behavioral_graph
from isr.core.graph import EdgeType, ISRGraph, NodeType
from isr.core.identity import Provenance, compute_content_hash, compute_revision_hash
from isr.core.invariants import validate_invariants

_SCHEMA_VERSION_RE = re.compile(r"^\d+\.\d+$")


class ISRRevision(BaseModel):
    """The immutable, content-addressed aggregate of an architecture state."""

    model_config = ConfigDict(frozen=True)

    system_id: str = Field(min_length=1)
    revision_id: str = Field(min_length=1)
    schema_version: str = Field(min_length=1)
    graph: ISRGraph
    provenance: Provenance
    content_hash: str = Field(min_length=64, max_length=64)
    revision_hash: str = Field(default="")

    @field_validator("schema_version")
    @classmethod
    def _schema_version_format(cls, value: str) -> str:
        if not _SCHEMA_VERSION_RE.match(value):
            raise ValueError(
                f"schema_version '{value}' must follow MAJOR.MINOR format (e.g. '1.0')"
            )
        return value

    @model_validator(mode="after")
    def _registered_schema_and_identity(self) -> "ISRRevision":
        from isr.schema.versions import SCHEMA_REGISTRY, validate_schema_graph

        validate_schema_graph(self.graph, self.schema_version)
        definition = SCHEMA_REGISTRY[self.schema_version]
        compatibility = {
            EdgeType(edge_name): (
                frozenset(NodeType(node_name) for node_name in source_types),
                frozenset(NodeType(node_name) for node_name in target_types),
            )
            for edge_name, (source_types, target_types)
            in definition.edge_compatibility.items()
        }
        # Direct Pydantic construction and model_validate must enforce the same
        # fail-closed invariants as the create() factory.
        validate_invariants(self.graph, edge_type_compatibility=compatibility)
        validate_behavioral_graph(self.graph)

        expected_content_hash = compute_content_hash(self.schema_version, self.graph)
        if self.content_hash != expected_content_hash:
            raise ValueError("ISR content_hash does not match canonical graph serialization")
        expected_revision_hash = compute_revision_hash(
            self.system_id, self.schema_version, self.content_hash, self.provenance
        )
        if not self.revision_hash:
            object.__setattr__(self, "revision_hash", expected_revision_hash)
        elif self.revision_hash != expected_revision_hash:
            raise ValueError("ISR revision_hash does not match its provenance envelope")
        return self

    @classmethod
    def create(
        cls,
        system_id: str,
        revision_id: str,
        schema_version: str,
        graph: ISRGraph,
        provenance: Provenance,
    ) -> ISRRevision:
        """Construct a revision, preserving domain exception types for callers."""
        from isr.schema.versions import SCHEMA_REGISTRY, validate_schema_graph

        validate_schema_graph(graph, schema_version)
        definition = SCHEMA_REGISTRY[schema_version]
        compatibility = {
            EdgeType(edge_name): (
                frozenset(NodeType(node_name) for node_name in source_types),
                frozenset(NodeType(node_name) for node_name in target_types),
            )
            for edge_name, (source_types, target_types)
            in definition.edge_compatibility.items()
        }
        validate_invariants(graph, edge_type_compatibility=compatibility)
        validate_behavioral_graph(graph)

        content_hash = compute_content_hash(schema_version, graph)
        revision_hash = compute_revision_hash(
            system_id, schema_version, content_hash, provenance
        )

        return cls(
            system_id=system_id,
            revision_id=revision_id,
            schema_version=schema_version,
            graph=graph,
            provenance=provenance,
            content_hash=content_hash,
            revision_hash=revision_hash,
        )
