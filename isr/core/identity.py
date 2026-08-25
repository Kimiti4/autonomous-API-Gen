"""Identity, provenance, and deterministic canonical hashing."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from typing import Sequence

from pydantic import BaseModel, ConfigDict, Field, field_validator

from isr.core.graph import ISRGraph

_SCHEMA_VERSION_RE = re.compile(r"^\d+\.\d+$")


class Provenance(BaseModel):
    model_config = ConfigDict(frozen=True)

    parent_revision_id: str | None = None
    requirement_refs: Sequence[str] = Field(default_factory=list)
    derivation_refs: Sequence[str] = Field(default_factory=list)
    created_by: str  # e.g. "genesis", "evolution_engine", "agent:architect"
    created_at: str  # ISO8601 UTC

    @field_validator("created_by")
    @classmethod
    def _created_by_non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("provenance.created_by must be a non-empty derivation origin")
        return value

    @field_validator("created_at")
    @classmethod
    def _created_at_iso8601(cls, value: str) -> str:
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("provenance.created_at must be an ISO8601 timestamp") from exc
        return value


def compute_content_hash(schema_version: str, graph: ISRGraph) -> str:
    """Deterministic canonicalization for content-addressing.

    Equivalent semantic content MUST produce the exact same hash regardless of
    insertion order of nodes, edges, or property keys.
    """
    canonical = {
        "schema_version": schema_version,
        "nodes": {
            key: node.model_dump(mode="json")
            for key, node in sorted(graph.nodes.items())
        },
        "edges": {
            key: edge.model_dump(mode="json")
            for key, edge in sorted(graph.edges.items())
        },
    }
    payload = json.dumps(
        canonical,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
