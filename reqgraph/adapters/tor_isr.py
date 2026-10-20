"""Canonical approved-TOR -> RequirementGraph -> Genesis ISR projection.

The TOR extractor preserves prose and requires human approval. This adapter
adds the second controlled step: an approval may carry explicit ISR node and
edge declarations, which the Genesis mapper projects into a validated ISR
revision. No architecture is inferred from requirement prose.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field

from genesis.mapper import GenesisResult, ReferenceDeterministicMapper
from isr.core.identity import Provenance
from isr.core.revision import ISRRevision
from reqgraph.core.graph import RequirementGraph
from reqgraph.ingestion.tor_extractor import HumanApproval, TORExtractionDraft

TOR_GENESIS_MAPPING = "tor-genesis-1.0"
TRACEABILITY_SCHEMA_ID = "esap.source-traceability"
TRACEABILITY_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class TORISRProjection:
    source_name: str
    source_sha256: str
    requirement_graph: RequirementGraph
    genesis: GenesisResult
    revision: ISRRevision
    mapping_spec_version: str


class SourceTraceability(BaseModel):
    """Immutable binding from reviewed source to ISR revision and plan."""

    model_config = ConfigDict(frozen=True)

    schema_id: str = TRACEABILITY_SCHEMA_ID
    schema_version: str = TRACEABILITY_SCHEMA_VERSION
    source_name: str
    source_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    requirement_graph_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    requirement_ids: tuple[str, ...]
    isr_content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    plan_id: str = Field(min_length=1)
    mapping_spec_version: str = Field(min_length=1)
    isr_node_ids: tuple[str, ...]
    isr_edge_ids: tuple[str, ...]


def requirement_graph_hash(requirements: RequirementGraph) -> str:
    """Deterministically hash the full reviewed requirement graph."""
    canonical = json.dumps(
        requirements.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _declared_ids(requirements: RequirementGraph) -> tuple[tuple[str, ...], tuple[str, ...]]:
    node_ids: set[str] = set()
    edge_ids: set[str] = set()
    for requirement in requirements.nodes.values():
        for declaration in requirement.properties.get("isr_nodes", ()):
            node_id = declaration.get("id") if isinstance(declaration, Mapping) else None
            if isinstance(node_id, str) and node_id:
                node_ids.add(node_id)
        for declaration in requirement.properties.get("isr_edges", ()):
            edge_id = declaration.get("id") if isinstance(declaration, Mapping) else None
            if isinstance(edge_id, str) and edge_id:
                edge_ids.add(edge_id)
    return tuple(sorted(node_ids)), tuple(sorted(edge_ids))


def project_tor_to_isr(
    draft: TORExtractionDraft,
    approvals: Mapping[str, HumanApproval],
    *,
    system_id: str,
    revision_id: str,
    created_at: str,
    mapping_spec_version: str = TOR_GENESIS_MAPPING,
) -> TORISRProjection:
    """Approve a draft and project it through the canonical Genesis seam."""
    requirements = draft.approve(approvals)
    unmapped = sorted(
        requirement_id
        for requirement_id, requirement in requirements.nodes.items()
        if not requirement.properties.get("isr_nodes")
        and not requirement.properties.get("isr_edges")
    )
    if unmapped:
        raise ValueError(
            "approved requirements have no explicit ISR declaration: "
            f"{unmapped}; add reviewer-authored isr_nodes/isr_edges"
        )
    genesis = ReferenceDeterministicMapper().map(requirements, mapping_spec_version)

    if genesis.coverage.uncovered:
        raise ValueError(
            f"Genesis left requirements without an ISR reference: {sorted(genesis.coverage.uncovered)}"
        )
    declared_node_ids, declared_edge_ids = _declared_ids(requirements)
    missing_nodes = sorted(set(declared_node_ids) - set(genesis.graph.nodes))
    missing_edges = sorted(set(declared_edge_ids) - set(genesis.graph.edges))
    if missing_nodes or missing_edges:
        raise ValueError(
            "reviewed ISR declarations were not projected; "
            f"nodes={missing_nodes}, edges={missing_edges}"
        )

    revision = ISRRevision.create(
        system_id=system_id,
        revision_id=revision_id,
        schema_version="1.0",
        graph=genesis.graph,
        provenance=Provenance(
            requirement_refs=tuple(sorted(requirements.nodes)),
            derivation_refs=(f"genesis:{mapping_spec_version}",),
            created_by="controlled_tor_extraction",
            created_at=created_at,
        ),
    )
    return TORISRProjection(
        source_name=draft.source_name,
        source_sha256=draft.source_sha256,
        requirement_graph=requirements,
        genesis=genesis,
        revision=revision,
        mapping_spec_version=mapping_spec_version,
    )


def traceability_record(
    projection: TORISRProjection,
    *,
    plan_id: str,
) -> SourceTraceability:
    """Build the content-bound record for evidence and artifact manifests."""
    declared_node_ids, declared_edge_ids = _declared_ids(projection.requirement_graph)
    return SourceTraceability(
        source_name=projection.source_name,
        source_sha256=projection.source_sha256,
        requirement_graph_hash=requirement_graph_hash(projection.requirement_graph),
        requirement_ids=tuple(sorted(projection.requirement_graph.nodes)),
        isr_content_hash=projection.revision.content_hash,
        plan_id=plan_id,
        mapping_spec_version=projection.mapping_spec_version,
        isr_node_ids=declared_node_ids,
        isr_edge_ids=declared_edge_ids,
    )
