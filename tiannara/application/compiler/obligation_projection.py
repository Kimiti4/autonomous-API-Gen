"""Deterministic, language-neutral projection from requirements to obligations.

This module projects the canonical RequirementGraph into a source-bound
obligation ledger. It intentionally does not infer architecture, select a
language/compiler, assign a runtime consumer, or certify enforcement. Those
remain explicit downstream decisions and evidence gates.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json

from tiannara.domain.models.compiler_obligation import (
    Applicability,
    CompilerObligationRecord,
    Disposition,
    Strength,
)
from tiannara.domain.models.requirement_graph import RequirementGraph, RequirementNode
from tiannara.domain.models.system_model import Priority


PROJECTION_SCHEMA = "tiannara.obligation-projection.v1"


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _project_node(graph: RequirementGraph, node: RequirementNode) -> CompilerObligationRecord:
    if node.priority is Priority.MUST:
        applicability, strength = Applicability.REQUIRED, Strength.MUST
    elif node.priority is Priority.SHOULD:
        applicability, strength = Applicability.OPTIONAL, Strength.SHOULD
    else:
        applicability, strength = Applicability.OPTIONAL, Strength.MAY

    # IDs remain stable when graph ordering changes; the graph hash binds the
    # record to the exact source revision. No implementation consumer is guessed.
    return CompilerObligationRecord(
        schema_version="1.0",
        obligation_id=f"requirement.{node.id}",
        source_graph_id=graph.graph_id,
        source_graph_hash=graph.content_hash(),
        domain=node.kind.value,
        statement=node.statement,
        acceptance_criteria=tuple(node.acceptance_criteria),
        rationale=node.rationale,
        applicability=applicability,
        required_strength=strength,
        enforcement_points=(),
        consumer_binding="",
        acceptance_scenarios=(),
        disposition=Disposition.UNKNOWN,
        limitations=("projection does not prove implementation or runtime enforcement",),
    )


@dataclass(frozen=True)
class ObligationProjection:
    """Immutable projection manifest for one exact requirement graph."""

    schema: str
    source_graph_id: str
    source_graph_hash: str
    records: tuple[CompilerObligationRecord, ...]
    projection_hash: str

    @property
    def required_obligation_ids(self) -> tuple[str, ...]:
        return tuple(sorted(
            record.obligation_id for record in self.records
            if record.applicability is Applicability.REQUIRED
        ))

    def canonical_payload(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "source_graph_id": self.source_graph_id,
            "source_graph_hash": self.source_graph_hash,
            "records": [
                {
                    **record.canonical_payload(),
                    "obligation_hash": record.obligation_hash,
                }
                for record in sorted(self.records, key=lambda item: item.obligation_id)
            ],
        }


def project_requirement_graph(graph: RequirementGraph) -> ObligationProjection:
    """Project every graph node, retaining unresolved implementation status."""
    graph_hash = graph.content_hash()
    records = tuple(
        _project_node(graph, node)
        for node in sorted(graph.nodes, key=lambda item: item.id)
    )
    if len({record.obligation_id for record in records}) != len(records):
        raise ValueError("requirement graph projection produced duplicate obligation IDs")
    payload = {
        "schema": PROJECTION_SCHEMA,
        "source_graph_id": graph.graph_id,
        "source_graph_hash": graph_hash,
        "records": [
            {**record.canonical_payload(), "obligation_hash": record.obligation_hash}
            for record in records
        ],
    }
    return ObligationProjection(
        schema=PROJECTION_SCHEMA,
        source_graph_id=graph.graph_id,
        source_graph_hash=graph_hash,
        records=records,
        projection_hash=_sha256(_canonical_bytes(payload)),
    )


def verify_obligation_projection(
    graph: RequirementGraph, projection: ObligationProjection
) -> None:
    """Recompute rather than trust a supplied manifest or hash."""
    expected = project_requirement_graph(graph)
    if projection.schema != expected.schema:
        raise ValueError("obligation projection schema is not supported")
    if (
        projection.source_graph_id != graph.graph_id
        or projection.source_graph_hash != graph.content_hash()
    ):
        raise ValueError("obligation projection does not match the active requirement graph")
    if tuple(record.model_dump(mode="json") for record in projection.records) != tuple(
        record.model_dump(mode="json") for record in expected.records
    ):
        raise ValueError("obligation projection records differ from the canonical source projection")
    if projection.projection_hash != expected.projection_hash:
        raise ValueError("obligation projection hash does not match recomputed canonical content")
