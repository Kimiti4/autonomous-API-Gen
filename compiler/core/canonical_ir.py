"""Canonical, versioned CompilerIR (D07) with deterministic identity and lineage.

CompilationPlan remains a downstream stabilization/execution projection. This
model is the compiler's technology-neutral record and preserves every source
ISR node and relationship, including semantics not yet consumed by emitters.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import NAMESPACE_URL, uuid5

from pydantic import BaseModel, ConfigDict, Field, model_validator

from compiler.core.capabilities import (
    BackendCapabilities, UnsupportedSemanticsError, assert_plan_supported,
    required_features, required_frontend_features,
)
from compiler.core.plan import CompilationPlan
from isr.core.graph import EdgeType
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


class CompilerIRProjectionReport(BaseModel):
    """Explicit source-to-transitional-plan coverage; no silent semantic loss."""

    model_config = ConfigDict(frozen=True)
    source_node_ids: tuple[str, ...]
    source_relationship_ids: tuple[str, ...]
    projected_node_ids: tuple[str, ...]
    projected_relationship_ids: tuple[str, ...]
    preserved_ir_only_node_ids: tuple[str, ...]
    preserved_ir_only_relationship_ids: tuple[str, ...]
    blocking_ir_only_node_ids: tuple[str, ...] = ()
    blocking_ir_only_relationship_ids: tuple[str, ...] = ()
    lost_node_ids: tuple[str, ...] = ()
    lost_relationship_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _complete_partition(self) -> "CompilerIRProjectionReport":
        source_nodes = set(self.source_node_ids)
        source_edges = set(self.source_relationship_ids)
        projected_nodes = set(self.projected_node_ids)
        projected_edges = set(self.projected_relationship_ids)
        ir_only_nodes = set(self.preserved_ir_only_node_ids)
        ir_only_edges = set(self.preserved_ir_only_relationship_ids)
        if projected_nodes & ir_only_nodes or projected_edges & ir_only_edges:
            raise ValueError("CompilerIR projection classifications overlap")
        if projected_nodes | ir_only_nodes | set(self.lost_node_ids) != source_nodes:
            raise ValueError("CompilerIR node projection report is incomplete")
        if projected_edges | ir_only_edges | set(self.lost_relationship_ids) != source_edges:
            raise ValueError("CompilerIR relationship projection report is incomplete")
        if not set(self.blocking_ir_only_node_ids).issubset(ir_only_nodes):
            raise ValueError("blocking IR-only node IDs must be preserved IR-only nodes")
        if not set(self.blocking_ir_only_relationship_ids).issubset(ir_only_edges):
            raise ValueError("blocking IR-only relationship IDs must be preserved IR-only relationships")
        if self.lost_node_ids or self.lost_relationship_ids:
            raise ValueError("CompilerIR cannot be created with unclassified semantic loss")
        return self


def _projection_report(revision: ISRRevision, plan: CompilationPlan) -> CompilerIRProjectionReport:
    projected_nodes = {
        item.id for item in (
            *plan.services, *plan.data_models, *plan.events,
            *plan.apis, *plan.effects, *plan.invariants, *plan.consequences,
            *plan.frontend_routes, *plan.frontend_interactions,
        )
    }
    projected_nodes.update(policy.policy_id for policy in plan.security)
    projected_edges: set[str] = {binding.edge_id for binding in plan.effect_bindings}

    service_by_id = {item.id: item for item in plan.services}
    api_by_id = {item.id: item for item in plan.apis}
    route_by_id = {item.id: item for item in plan.frontend_routes}
    interaction_by_id = {item.id: item for item in plan.frontend_interactions}
    consequence_by_id = {item.id: item for item in plan.consequences}
    for edge in revision.graph.edges.values():
        source_service = service_by_id.get(edge.source_id)
        target_api = api_by_id.get(edge.target_id)
        if edge.type == EdgeType.EXPOSES:
            if target_api is not None and target_api.service_id == edge.source_id:
                projected_edges.add(edge.id)
        elif edge.type == EdgeType.PERSISTS:
            if source_service is not None and any(
                item.id == edge.target_id for item in source_service.data_models
            ):
                projected_edges.add(edge.id)
        elif edge.type == EdgeType.PUBLISHES:
            if source_service is not None and any(
                item.id == edge.target_id for item in source_service.published_events
            ):
                projected_edges.add(edge.id)
        elif edge.type == EdgeType.CONSUMED_BY:
            target_service = service_by_id.get(edge.target_id)
            if target_service is not None and any(
                item.id == edge.source_id for item in target_service.consumed_events
            ):
                projected_edges.add(edge.id)
        elif edge.type == EdgeType.SECURED_BY:
            policy_id = edge.target_id
            service = service_by_id.get(edge.source_id)
            api = api_by_id.get(edge.source_id)
            if (service and any(p.policy_id == policy_id for p in service.security_policies)) or (
                api and any(p.policy_id == policy_id for p in api.security_policies)
            ):
                projected_edges.add(edge.id)
        elif edge.type == EdgeType.ROUTES_TO:
            route = route_by_id.get(edge.source_id)
            if route and any(api.id == edge.target_id for api in route.api_operations):
                projected_edges.add(edge.id)
        elif edge.type == EdgeType.INVOKES:
            interaction = interaction_by_id.get(edge.source_id)
            if interaction and interaction.target_api_operation is not None and (
                interaction.target_api_operation.id == edge.target_id
            ):
                projected_edges.add(edge.id)
        elif edge.type == EdgeType.CONTAINS:
            route = route_by_id.get(edge.source_id)
            if route and any(item.id == edge.target_id for item in route.interactions):
                projected_edges.add(edge.id)
        elif edge.type == EdgeType.REQUIRES_INVARIANT:
            if any(binding.edge_id == edge.id for binding in plan.invariant_bindings):
                projected_edges.add(edge.id)
        elif edge.type == EdgeType.CONSEQUENCE_OF:
            consequence = consequence_by_id.get(edge.source_id)
            if consequence and edge.target_id in consequence.related_node_ids:
                projected_edges.add(edge.id)

    source_nodes = {node.id for node in revision.graph.nodes.values()}
    source_edges = {edge.id for edge in revision.graph.edges.values()}
    source_node_ids = tuple(sorted(source_nodes))
    source_relationship_ids = tuple(sorted(source_edges))
    projected_node_ids = tuple(sorted(projected_nodes & source_nodes))
    projected_relationship_ids = tuple(sorted(projected_edges & source_edges))
    node_by_id = {node.id: node for node in revision.graph.nodes.values()}
    edge_by_id = {edge.id: edge for edge in revision.graph.edges.values()}
    ir_only_nodes = source_nodes - set(projected_node_ids)
    ir_only_edges = source_edges - set(projected_relationship_ids)
    blocking_nodes = tuple(sorted(
        node_id for node_id in ir_only_nodes
        if node_by_id[node_id].properties.get("required_for_backend") is True
        or node_by_id[node_id].properties.get("backend_required") is True
    ))
    blocking_edges = tuple(sorted(
        edge_id for edge_id in ir_only_edges
        if edge_by_id[edge_id].properties.get("required_for_backend") is True
        or edge_by_id[edge_id].properties.get("backend_required") is True
    ))
    return CompilerIRProjectionReport(
        source_node_ids=source_node_ids,
        source_relationship_ids=source_relationship_ids,
        projected_node_ids=projected_node_ids,
        projected_relationship_ids=projected_relationship_ids,
        preserved_ir_only_node_ids=tuple(sorted(ir_only_nodes)),
        preserved_ir_only_relationship_ids=tuple(sorted(ir_only_edges)),
        blocking_ir_only_node_ids=blocking_nodes,
        blocking_ir_only_relationship_ids=blocking_edges,
    )


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
    projection_report: CompilerIRProjectionReport
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
        if set(self.projection_report.source_node_ids) != {item.source_node_id for item in self.nodes}:
            raise ValueError("CompilerIR projection report/source node inventory mismatch")
        if set(self.projection_report.source_relationship_ids) != {item.source_edge_id for item in self.relationships}:
            raise ValueError("CompilerIR projection report/source relationship inventory mismatch")
        if self.provenance.source_isr_revision_id != self.source_isr_revision_id:
            raise ValueError("CompilerIR provenance/source ISR revision ID mismatch")
        if self.provenance.lowering_operator != self.lowering_operator:
            raise ValueError("CompilerIR provenance/lowering operator mismatch")
        if self.provenance.lowering_timestamp != self.lowering_timestamp:
            raise ValueError("CompilerIR provenance/lowering timestamp mismatch")
        if self.provenance.lowering_chain != self.lowering_chain:
            raise ValueError("CompilerIR provenance/lowering chain mismatch")
        expected_capabilities = sorted(
            {feature.value for feature in required_features(self.execution_plan)}
            | {feature.value for feature in required_frontend_features(self.execution_plan)}
        )
        if sorted(self.required_capabilities) != expected_capabilities:
            raise ValueError("CompilerIR required_capabilities do not match its execution projection")
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
        backend_constraints: tuple[str, ...] = (),
        lowering_timestamp: str | None = None,
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
                    value for value in (
                        node.properties.get("source_requirement_ids", ())
                        if isinstance(node.properties.get("source_requirement_ids", ()), (list, tuple, set, frozenset))
                        else ()
                    ) if isinstance(value, str)
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
        projection_report = _projection_report(revision, execution_plan)
        capabilities = sorted(
            {feature.value for feature in required_features(execution_plan)}
            | {feature.value for feature in required_frontend_features(execution_plan)}
        )
        operator = "compiler.core.lowering.isr_revision_to_compiler_ir@1.0.0"
        timestamp = lowering_timestamp or datetime.now(timezone.utc).isoformat()
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
            "projection_report": projection_report.model_dump(mode="json"),
            "execution_plan": execution_plan.model_dump(mode="json"),
            "backend_constraints": list(backend_constraints),
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



def assert_compiler_ir_supported(
    compiler_ir: CompilerIR,
    capabilities: BackendCapabilities,
) -> None:
    """Enforce target constraints and semantic capability checks before lowering."""
    if compiler_ir.projection_report.blocking_ir_only_node_ids or compiler_ir.projection_report.blocking_ir_only_relationship_ids:
        raise UnsupportedSemanticsError(
            "CompilerIR contains backend-required semantics outside the transitional plan projection: "
            f"nodes={compiler_ir.projection_report.blocking_ir_only_node_ids}, "
            f"relationships={compiler_ir.projection_report.blocking_ir_only_relationship_ids}"
        )
    if compiler_ir.backend_constraints and capabilities.backend_id not in compiler_ir.backend_constraints:
        raise UnsupportedSemanticsError(
            f"Backend {capabilities.backend_id!r} is excluded by CompilerIR constraints "
            f"{compiler_ir.backend_constraints}"
        )
    assert_plan_supported(compiler_ir.execution_plan, capabilities)
