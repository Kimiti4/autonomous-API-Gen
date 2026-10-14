"""Source-bound, technology-neutral projection from requirements to obligations.

This is a shared compiler-domain contract, not a TaskFlow-specific generator.
It preserves source identity and graph traceability across language/compiler
backends. Projection yields UNKNOWN obligations; it never claims implementation
or runtime enforcement merely because a requirement was parsed.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Iterable

from pydantic import BaseModel, ConfigDict, Field, model_validator

from tiannara.domain.models.compiler_obligation import (
    Applicability,
    CompilerObligationRecord,
    Disposition,
    Strength,
)
from tiannara.domain.models.requirement_graph import RequirementGraph
from tiannara.domain.models.semantic_resolution import (
    SemanticResolutionRecord,
    require_resolved_semantics,
)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


class SourceProjectionContext(BaseModel):
    """Immutable identity binding for one source snapshot and its semantic graph.

    snapshot_sha256 is computed from exact source bytes by the factory below.
    graph_json is a canonical frozen snapshot, not a live mutable graph object.
    Semantic resolution is bound to the graph ID/hash and retained in the
    context so a downstream consumer can revalidate it before using it.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: str = "source-projection-context.v1"
    source_id: str = Field(min_length=1, max_length=512)
    snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    graph_id: str = Field(min_length=1, max_length=256)
    graph_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    graph_json: str = Field(min_length=2)
    semantic_resolution: SemanticResolutionRecord
    context_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def verify_context_integrity(self) -> "SourceProjectionContext":
        try:
            graph_payload = json.loads(self.graph_json)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValueError("graph_json must contain canonical JSON") from exc
        canonical_graph = canonical_json_bytes(graph_payload).decode("utf-8")
        if canonical_graph != self.graph_json:
            raise ValueError("graph_json is not canonical")
        if graph_payload.get("graph_id") != self.graph_id:
            raise ValueError("graph identity does not match frozen graph payload")
        actual_graph_hash = sha256_bytes(
            canonical_json_bytes({
                key: value for key, value in graph_payload.items()
                if key != "analysis"
            })
        )
        # RequirementGraph.content_hash uses the project's canonical_hash,
        # which is SHA-256 over canonical JSON. Recompute through that contract
        # rather than accepting a caller-supplied graph hash.
        if actual_graph_hash != self.graph_sha256:
            raise ValueError("graph hash does not match frozen graph payload")
        if (
            self.semantic_resolution.graph_id != self.graph_id
            or self.semantic_resolution.graph_hash != self.graph_sha256
        ):
            raise ValueError("semantic resolution is not bound to this graph")
        payload = {
            "schema_version": self.schema_version,
            "source_id": self.source_id,
            "snapshot_sha256": self.snapshot_sha256,
            "graph_id": self.graph_id,
            "graph_sha256": self.graph_sha256,
            "graph_json": self.graph_json,
            "semantic_resolution": self.semantic_resolution.model_dump(mode="json"),
        }
        expected_context_hash = sha256_bytes(canonical_json_bytes(payload))
        if self.context_sha256 != expected_context_hash:
            raise ValueError("projection context hash does not match canonical content")
        return self


def create_source_projection_context(
    *,
    source_id: str,
    source_bytes: bytes,
    graph: RequirementGraph,
    semantic_resolution: SemanticResolutionRecord,
) -> SourceProjectionContext:
    """Freeze exact source bytes, graph, and graph-bound semantic resolution."""
    if not source_id.strip():
        raise ValueError("source_id must not be blank")
    if not isinstance(source_bytes, bytes) or not source_bytes:
        raise ValueError("source_bytes must be non-empty bytes")
    graph_hash = graph.content_hash()
    if (
        semantic_resolution.graph_id != graph.graph_id
        or semantic_resolution.graph_hash != graph_hash
    ):
        raise ValueError("semantic resolution does not match the supplied graph")
    graph_payload = graph.model_dump(mode="json", exclude={"analysis"})
    graph_json = canonical_json_bytes(graph_payload).decode("utf-8")
    values = {
        "schema_version": "source-projection-context.v1",
        "source_id": source_id,
        "snapshot_sha256": sha256_bytes(source_bytes),
        "graph_id": graph.graph_id,
        "graph_sha256": graph_hash,
        "graph_json": graph_json,
        "semantic_resolution": semantic_resolution.model_dump(mode="json"),
    }
    return SourceProjectionContext(
        **values,
        context_sha256=sha256_bytes(canonical_json_bytes(values)),
    )


@dataclass(frozen=True)
class ObligationProjectionResult:
    context_sha256: str
    source_id: str
    snapshot_sha256: str
    graph_id: str
    graph_sha256: str
    records: tuple[CompilerObligationRecord, ...]
    unresolved_semantics: tuple[str, ...]
    blockers: tuple[str, ...]

    @property
    def generation_allowed(self) -> bool:
        return not self.blockers and not self.unresolved_semantics


def project_obligations(
    context: SourceProjectionContext,
    *,
    require_resolved_semantics_before_generation: bool = True,
) -> ObligationProjectionResult:
    """Derive exactly one UNKNOWN obligation per graph node, without guessing.

    This is intentionally backend-agnostic. Backend adapters consume the same
    obligation IDs and source hashes; language-specific enforcement is verified
    later by consumer-bound acceptance evidence. An unresolved semantic ledger
    blocks generation but does not erase the requirements from the ledger.
    """
    payload = json.loads(context.graph_json)
    graph = RequirementGraph.model_validate(payload)
    if graph.content_hash() != context.graph_sha256:
        raise ValueError("frozen graph failed canonical hash revalidation")
    if graph.graph_id != context.graph_id:
        raise ValueError("frozen graph identity changed")
    resolutions = context.semantic_resolution
    if resolutions.graph_id != graph.graph_id or resolutions.graph_hash != graph.content_hash():
        raise ValueError("semantic resolution binding changed")

    records: list[CompilerObligationRecord] = []
    for node in graph.nodes:
        strength = {
            "must": Strength.MUST,
            "should": Strength.SHOULD,
            "could": Strength.MAY,
        }.get(node.priority.value, Strength.MUST)
        records.append(CompilerObligationRecord(
            schema_version="1.0",
            obligation_id=f"requirement.{node.id}",
            source_graph_id=graph.graph_id,
            source_graph_hash=graph.content_hash(),
            domain=node.kind.value,
            statement=node.statement,
            acceptance_criteria=tuple(node.acceptance_criteria),
            rationale=node.rationale,
            applicability=Applicability.REQUIRED,
            required_strength=strength,
            disposition=Disposition.UNKNOWN,
            limitations=(
                "Projection establishes traceability only; implementation and runtime enforcement are unverified.",
            ),
        ))

    unresolved = resolutions.unresolved_fields()
    blockers: list[str] = []
    if not records:
        blockers.append("source graph contains no obligations")
    if require_resolved_semantics_before_generation and unresolved:
        blockers.append(
            "mandatory semantic decisions remain unresolved: " + ", ".join(unresolved)
        )
    if any(record.source_graph_hash != context.graph_sha256 for record in records):
        blockers.append("projected obligation source hash mismatch")
    return ObligationProjectionResult(
        context_sha256=context.context_sha256,
        source_id=context.source_id,
        snapshot_sha256=context.snapshot_sha256,
        graph_id=context.graph_id,
        graph_sha256=context.graph_sha256,
        records=tuple(records),
        unresolved_semantics=tuple(unresolved),
        blockers=tuple(blockers),
    )


def verify_exact_projection(
    context: SourceProjectionContext,
    supplied_records: Iterable[CompilerObligationRecord],
) -> tuple[str, ...]:
    """Return blockers if caller-supplied records omit or alter projected truth."""
    expected = project_obligations(
        context, require_resolved_semantics_before_generation=False
    ).records
    expected_by_id = {record.obligation_id: record for record in expected}
    actual_by_id: dict[str, CompilerObligationRecord] = {}
    blockers: list[str] = []
    for record in supplied_records:
        if record.obligation_id in actual_by_id:
            blockers.append(f"duplicate supplied obligation: {record.obligation_id}")
        else:
            actual_by_id[record.obligation_id] = record
    missing = sorted(set(expected_by_id) - set(actual_by_id))
    extra = sorted(set(actual_by_id) - set(expected_by_id))
    if missing:
        blockers.append(f"projected obligations omitted: {missing}")
    if extra:
        blockers.append(f"unprojected obligations supplied: {extra}")
    for obligation_id in sorted(set(expected_by_id) & set(actual_by_id)):
        expected_record = expected_by_id[obligation_id]
        actual_record = actual_by_id[obligation_id]
        if actual_record.canonical_payload() != expected_record.canonical_payload():
            blockers.append(f"projected obligation was altered: {obligation_id}")
    return tuple(blockers)
