"""Provenance manifest schema for a materialized repository (Phase 17).

``provenance/manifest.json`` is the audit anchor traced through the
RepositoryMaterializer: it links the committed repository back to the original
intent and the ISR, records which backends compiled what, and preserves the
verification outcome (including any ``--force`` override) so downstream
stages -- evolution (Phase 20), evidence ledgering, certification -- consume a
lineage-complete record.

These are pure data models (domain layer): they depend only on serializable
fields. The factory that derives them from compiler outputs lives in
``tiannara/application/materializer/provenance_builder.py``.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class VerificationManifest(BaseModel):
    ok: bool
    forced: bool
    details: dict[str, Any] = Field(default_factory=dict)


class BackedManifest(BaseModel):
    backend_id: str
    system_name: str
    capability_manifest: dict[str, Any] | None = None
    verification: VerificationManifest


class ProvenanceManifest(BaseModel):
    schema_version: str = "1.0"
    build_id: str
    intent_hash: str  # sha256 of the natural-language intent (statement_hash)
    isr_hash: str
    plan_id: str
    policy_name: str | None = (
        None  # ProjectCompilationReport does not carry it (tree limitation)
    )
    backend_ids: list[str] = Field(default_factory=list)
    capability_manifests: list[BackedManifest] = Field(default_factory=list)
    verification: VerificationManifest
