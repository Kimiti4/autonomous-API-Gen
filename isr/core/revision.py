"""The immutable, content-addressed ISR revision."""

from __future__ import annotations

import re
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

from isr.core.graph import ISRGraph
from isr.core.identity import Provenance, compute_content_hash
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

    _EXPECTED_CONTENT_HASH: ClassVar[int] = 64

    @field_validator("schema_version")
    @classmethod
    def _schema_version_format(cls, value: str) -> str:
        if not _SCHEMA_VERSION_RE.match(value):
            raise ValueError(
                f"schema_version '{value}' must follow MAJOR.MINOR format (e.g. '1.0')"
            )
        return value

    @classmethod
    def create(
        cls,
        system_id: str,
        revision_id: str,
        schema_version: str,
        graph: ISRGraph,
        provenance: Provenance,
    ) -> ISRRevision:
        """Construct a revision, enforcing all invariants fail-closed."""
        validate_invariants(graph)

        content_hash = compute_content_hash(schema_version, graph)

        return cls(
            system_id=system_id,
            revision_id=revision_id,
            schema_version=schema_version,
            graph=graph,
            provenance=provenance,
            content_hash=content_hash,
        )
