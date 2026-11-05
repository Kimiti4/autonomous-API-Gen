"""Canonical, versioned CompilerIR (D07) with deterministic identity and lineage.

CompilationPlan remains a downstream stabilization/execution projection. This
model is the compiler's technology-neutral record and preserves every source
ISR node and relationship, including semantics not yet consumed by emitters.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Literal
from uuid import NAMESPACE_URL, uuid5

from pydantic import BaseModel, ConfigDict, Field, model_validator

from compiler.core.capabilities import required_features, required_frontend_features
from compiler.core.plan import CompilationPlan
from isr.core.revision import ISRRevision

_SHA256_RE = re.compile(r"^[a-f0-9]{64}$")


class CompilerIRNode(BaseModel):
    model_config = ConfigDict(frozen=True)
    source_node_id: str = Field(min_length=1)
    semantic_type: str = Field(min_length=1)
    properties: dict[str, Any] = Field(default_factory=dict)
    source_requirement_ids: tuple[str, ...] = ()


class CompilerIRRelationship(BaseModel):
    model_config = ConfigDict(frozen=True)
    source_edge_id: str = Field(min_length=1)
    semantic_type: str = Field(min_length=1)
    source_node_id: str = Field(min_length=1)
    target_node_id: str = Field(min_length=1)
    properties: dict[str, Any] = Field(default_factory=dict)


class CompilerIRProvenance(BaseModel):
    model_config = ConfigDict(frozen=True)
    source_isr_revision_id: str = Field(min_length=1)
    source_isr_content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_isr_revision_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_architecture_candidate_content_hash: str | None = Field(
        default=None, pattern=r"^[a-f0-9]{64}$"
    )
    lowering_operator: str = Field(min_length=1)
    lowering_timestamp: str = Field(min_length=1)
    lowering_chain: tuple[str, ...] = ()


class CompilerIR(BaseModel):
    """Frozen canonical compiler representation; never a backend-specific AST."""

    model_config = ConfigDict(frozen=True)

    compilation_id: str = Field(min_length=1)
    schema_version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    source_isr_revision_id: str = Field(min_length=1)
    source_isr_content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_isr_revision_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_architecture_candidate_content_hash: str | None = Field(
        default=None, pattern=r"^[a-f0-9]{64}$"
    )
    architecture_reference_state: Literal["BOUND", "NOT_APPLICABLE"]
    architecture_reference_reason: str | None = None
    nodes: tuple[CompilerIRNode, ...]
    relationships: tuple[CompilerIRRelationship, ...]
    execution_plan: CompilationPlan
    backend_constraints: tuple[str, ...] = ()
    required_capabilities: tuple[str, ...] = ()
    provenance: CompilerIRProvenance
    lowering_operator: str = Field(min_length=1)
    lowering_timestamp: str = Field(min_length=1)
    lowering_chain: tuple[str, ...] = ()
    content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def _lineage_is_explicit(self) -> "CompilerIR":
        if self.architecture_reference_state == "BOUND":
            if not self.source_architecture_candidate_content_hash:
                raise ValueError("BOUND architecture reference requires a content hash")
            if self.architecture_reference_reason is not None:
                raise ValueError("BOUND architecture reference must not carry a not-applicable reason")
        else:
            if self.source_architecture_candidate_content_hash is not None:
                raise ValueError("NOT_APPLICABLE architecture reference cannot carry a content hash")
            if not (self.architecture_reference_reason or "").strip():
                raise ValueError("NOT_APPLICABLE architecture reference requires an explicit reason")
        if self.provenance.source_isr_content_hash != self.source_isr_content_hash:
            raise ValueError("CompilerIR provenance/source ISR graph hash mismatch")
        if self.provenance.source_isr_revision_hash != self.source_isr_revision_hash:
            raise ValueError("CompilerIR provenance/source ISR revision hash mismatch")
        if self.provenance.source_architecture_candidate_content_hash != self.source_architecture_candidate_content_hash:
            raise ValueError("CompilerIR provenance/source architecture hash mismatch")
        expected = self.compute_content_hash(self.model_dump(mode="json", exclude={"content_hash"}))
        if expected != self.content_hash:
            raise ValueError("CompilerIR content_hash does not match canonical serialization")
        return self

    @staticmethod
    def canonical_json(payload: dict[str, Any]) -> str:
        return json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )

    @classmethod
    def compute_content_hash(cls, payload: dict[str, Any]) -> str:
        return hashlib.sha256(cls.canonical_json(payload).encode("utf-8")).hexdigest()

    @classmethod
    def from_revision(
        cls,
        revision: ISRRevision,
        execution_plan: CompilationPlan,
        *,
        source_architecture_candidate_content_hash: str | None = None,
        architecture_reference_reason: str | None = None,
    ) -> "CompilerIR":
        if source_architecture_candidate_content_hash is None and not architecture_reference_reason:
            raise ValueError(
                "Supply an ArchitectureCandidate content hash or an explicit "
                "reason why this source route has no ArchitectureCandidate"
            )
        if source_architecture_candidate_content_hash is not None and not _SHA256_RE.fullmatch(
            source_architecture_candidate_content_hash
        ):
            raise ValueError("ArchitectureCandidate content hash must be a SHA-256 hex digest")

        nodes = tuple(
            CompilerIRNode(
                source_node_id=node.id,
                semantic_type=node.type.value,
                properties=dict(node.properties),
                source_requirement_ids=tuple(sorted(
                    value for value in node.properties.get("source_requirement_ids", ())
                    if isinstance(value, str)
                )),
            )
            for _, node in sorted(revision.graph.nodes.items())
        )
        relationships = tuple(
            CompilerIRRelationship(
                source_edge_id=edge.id,
                semantic_type=edge.type.value,
                source_node_id=edge.source_id,
                target_node_id=edge.target_id,
                properties=dict(edge.properties),
            )
            for _, edge in sorted(revision.graph.edges.items())
        )
        capabilities = sorted(
            {feature.value for feature in required_features(execution_plan)}
            | {feature.value for feature in required_frontend_features(execution_plan)}
        )
        operator = "compiler.core.lowering.isr_revision_to_compiler_ir@1.0.0"
        timestamp = revision.provenance.created_at
        chain = (
            "isr.core.revision.ISRRevision",
            "compiler.core.canonical_ir.CompilerIR",
            "compiler.core.plan.CompilationPlan[transitional-execution-projection]",
        )
        provenance = CompilerIRProvenance(
            source_isr_revision_id=revision.revision_id,
            source_isr_content_hash=revision.content_hash,
            source_isr_revision_hash=revision.revision_hash,
            source_architecture_candidate_content_hash=source_architecture_candidate_content_hash,
            lowering_operator=operator,
            lowering_timestamp=timestamp,
            lowering_chain=chain,
        )
        state: Literal["BOUND", "NOT_APPLICABLE"] = (
            "BOUND" if source_architecture_candidate_content_hash else "NOT_APPLICABLE"
        )
        base = {
            "schema_version": "1.0.0",
            "source_isr_revision_id": revision.revision_id,
            "source_isr_content_hash": revision.content_hash,
            "source_isr_revision_hash": revision.revision_hash,
            "source_architecture_candidate_content_hash": source_architecture_candidate_content_hash,
            "architecture_reference_state": state,
            "architecture_reference_reason": architecture_reference_reason,
            "nodes": [item.model_dump(mode="json") for item in nodes],
            "relationships": [item.model_dump(mode="json") for item in relationships],
            "execution_plan": execution_plan.model_dump(mode="json"),
            "backend_constraints": [],
            "required_capabilities": capabilities,
            "provenance": provenance.model_dump(mode="json"),
            "lowering_operator": operator,
            "lowering_timestamp": timestamp,
            "lowering_chain": list(chain),
        }
        identity_digest = cls.compute_content_hash(base)
        compilation_id = str(uuid5(NAMESPACE_URL, f"esap:compiler-ir:{identity_digest}"))
        with_identity = {"compilation_id": compilation_id, **base}
        content_hash = cls.compute_content_hash(with_identity)
        return cls(
            compilation_id=compilation_id,
            **base,
            content_hash=content_hash,
        )
