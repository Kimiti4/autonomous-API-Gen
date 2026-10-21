"""Deterministic TOR candidate extraction with mandatory human approval.

This module never converts prose directly into an implementation-ready ISR.
It preserves source spans, produces reviewable candidates, and permits
RequirementGraph construction only after an explicit approval record exists
for every candidate.
"""
from __future__ import annotations

import hashlib
import re
from enum import Enum
from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field, model_validator

from reqgraph.core.graph import (
    Priority,
    RequirementGraph,
    RequirementKind,
    RequirementNode,
)
from reqgraph.core.invariants import validate_requirement_graph


class ReviewStatus(str, Enum):
    NEEDS_REVIEW = "needs_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class TORCandidate(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    requirement_id: str
    statement: str = Field(min_length=1)
    proposed_kind: RequirementKind
    proposed_priority: Priority
    ambiguity_score: float = Field(ge=0.0, le=1.0)
    ambiguity_reasons: tuple[str, ...] = ()
    section: str | None = None
    source_ref: str
    source_start_line: int = Field(ge=1)
    source_end_line: int = Field(ge=1)
    status: ReviewStatus = ReviewStatus.NEEDS_REVIEW


class HumanApproval(BaseModel):
    """Explicit human decision required before a draft enters RequirementGraph.

    ``isr_nodes`` and ``isr_edges`` are optional, reviewer-authored architecture
    declarations. They are validated against the approved requirement IDs and
    projected by the Genesis mapper; they are never inferred from prose.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")
    reviewer_id: str = Field(min_length=1)
    approval_ref: str = Field(min_length=1)
    acceptance_criteria: tuple[str, ...] = Field(min_length=1)
    selected_kind: RequirementKind | None = None
    selected_priority: Priority | None = None
    resolution_ref: str | None = None
    isr_nodes: tuple[dict[str, Any], ...] = ()
    isr_edges: tuple[dict[str, Any], ...] = ()


def _require_source_binding(
    properties: Mapping[str, Any],
    requirement_id: str,
    candidate_ids: set[str],
    label: str,
    declaration_id: str,
) -> None:
    source_ids = properties.get("source_requirement_ids")
    if not isinstance(source_ids, (list, tuple)) or not source_ids:
        raise ValueError(
            f"{label} {declaration_id!r} must cite source_requirement_ids including {requirement_id!r}"
        )
    unknown = sorted(
        source_id
        for source_id in source_ids
        if not isinstance(source_id, str) or source_id not in candidate_ids
    )
    if unknown:
        raise ValueError(
            f"{label} {declaration_id!r} cites unknown source requirement IDs: {unknown}"
        )
    if requirement_id not in source_ids:
        raise ValueError(
            f"{label} {declaration_id!r} must cite its approving requirement {requirement_id!r}"
        )


def _validate_declarations(
    approval: "HumanApproval",
    requirement_id: str,
    candidate_ids: set[str],
    declared_node_ids: set[str],
    declared_edge_ids: set[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    nodes: list[dict[str, Any]] = []
    for declaration in approval.isr_nodes:
        node_id = declaration.get("id")
        node_type = declaration.get("type")
        properties = declaration.get("properties")
        if not isinstance(node_id, str) or not node_id:
            raise ValueError(f"requirement {requirement_id!r} ISR node needs a non-empty id")
        if not isinstance(node_type, str) or not node_type:
            raise ValueError(f"ISR node {node_id!r} needs a non-empty type")
        if not isinstance(properties, Mapping):
            raise ValueError(f"ISR node {node_id!r} needs a properties mapping")
        if node_id in declared_node_ids:
            raise ValueError(f"duplicate ISR node declaration: {node_id!r}")
        _require_source_binding(properties, requirement_id, candidate_ids, "ISR node", node_id)
        declared_node_ids.add(node_id)
        nodes.append(dict(declaration))

    edges: list[dict[str, Any]] = []
    for declaration in approval.isr_edges:
        edge_id = declaration.get("id")
        edge_type = declaration.get("type")
        source_id = declaration.get("source_id")
        target_id = declaration.get("target_id")
        properties = declaration.get("properties", {})
        if not all(
            isinstance(value, str) and value
            for value in (edge_id, edge_type, source_id, target_id)
        ):
            raise ValueError(
                f"requirement {requirement_id!r} ISR edge needs id/type/source_id/target_id"
            )
        if not isinstance(properties, Mapping):
            raise ValueError(f"ISR edge {edge_id!r} needs a properties mapping")
        if edge_id in declared_edge_ids:
            raise ValueError(f"duplicate ISR edge declaration: {edge_id!r}")
        _require_source_binding(properties, requirement_id, candidate_ids, "ISR edge", edge_id)
        declared_edge_ids.add(edge_id)
        edges.append(dict(declaration))

    return nodes, edges


class TORExtractionDraft(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    source_name: str = Field(min_length=1)
    source_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_text: str = Field(min_length=1)
    schema_version: str = "1.0"
    candidates: tuple[TORCandidate, ...] = ()

    @model_validator(mode="after")
    def validate_source_digest(self) -> "TORExtractionDraft":
        actual = hashlib.sha256(self.source_text.encode("utf-8")).hexdigest()
        if actual != self.source_sha256:
            raise ValueError("source_sha256 does not match preserved source_text")
        return self

    def approve(
        self,
        approvals: Mapping[str, HumanApproval],
    ) -> RequirementGraph:
        """Build a validated graph only when every extracted item is approved."""
        if hashlib.sha256(self.source_text.encode("utf-8")).hexdigest() != self.source_sha256:
            raise ValueError("TOR source changed after extraction; re-extract and re-review")
        if not self.candidates:
            raise ValueError("cannot approve a TOR extraction with zero requirement candidates")
        candidate_ids = {candidate.requirement_id for candidate in self.candidates}
        missing = sorted(candidate_ids - set(approvals))
        extra = sorted(set(approvals) - candidate_ids)
        if missing or extra:
            raise ValueError(
                f"approval set must match extracted candidates; missing={missing}, extra={extra}"
            )

        nodes: dict[str, RequirementNode] = {}
        declared_node_ids: set[str] = set()
        declared_edge_ids: set[str] = set()
        for candidate in self.candidates:
            approval = approvals[candidate.requirement_id]
            if not approval.acceptance_criteria:
                raise ValueError(
                    f"Requirement {candidate.requirement_id!r} needs explicit acceptance criteria"
                )
            kind = approval.selected_kind or candidate.proposed_kind
            priority = approval.selected_priority or candidate.proposed_priority
            if candidate.ambiguity_score > 0.5 and not approval.resolution_ref:
                raise ValueError(
                    f"Requirement {candidate.requirement_id!r} needs a recorded ambiguity resolution"
                )
            isr_nodes, isr_edges = _validate_declarations(
                approval,
                candidate.requirement_id,
                candidate_ids,
                declared_node_ids,
                declared_edge_ids,
            )
            properties: dict[str, Any] = {
                "source_name": self.source_name,
                "source_sha256": self.source_sha256,
                "source_start_line": candidate.source_start_line,
                "source_end_line": candidate.source_end_line,
                "section": candidate.section or "",
                "ambiguity_reasons": list(candidate.ambiguity_reasons),
                "review_status": ReviewStatus.APPROVED.value,
                "reviewer_id": approval.reviewer_id,
                "approval_ref": approval.approval_ref,
            }
            if isr_nodes:
                properties["isr_nodes"] = isr_nodes
            if isr_edges:
                properties["isr_edges"] = isr_edges
            nodes[candidate.requirement_id] = RequirementNode(
                id=candidate.requirement_id,
                kind=kind,
                statement=candidate.statement,
                priority=priority,
                acceptance_criteria=approval.acceptance_criteria,
                ambiguity_score=candidate.ambiguity_score,
                resolution_ref=approval.resolution_ref,
                source_refs=(candidate.source_ref,),
                properties=properties,
            )
        graph = RequirementGraph(
            schema_version=self.schema_version,
            nodes=nodes,
            edges={},
        )
        validate_requirement_graph(graph)
        return graph


_HEADING = re.compile(
    r"^\s*(?:(?:\d+(?:\.\d+)*[.)]?)\s*)?[A-Z][A-Z0-9 &()/,:-]{2,}\s*$"
)
_BULLET = re.compile(r"^\s*(?:[-*•]\s+|[a-zA-Z][.)]\s+|\d+[.)]\s+)(.+?)\s*$")
_MODAL = re.compile(r"\b(?:shall|must|should|required to|needs to|will provide|must provide)\b", re.I)
_ACTION = re.compile(
    r"\b(?:provide|support|allow|include|generate|maintain|ensure|automate|"
    r"integrate|track|calculate|process|manage|secure|backup|recover|"
    r"distribute|access|update|download|allocate|record|retain|demonstrate|submit|deliver|disclose|conduct|apply|view|retrieve|import|export)\b",
    re.I,
)
_VAGUE = (
    "as applicable",
    "where applicable",
    "appropriate",
    "user-friendly",
    "reasonable",
    "etc.",
    "and so on",
    "where possible",
)
_NON_FUNCTIONAL = (
    "security", "secure", "backup", "recovery", "performance", "availability",
    "browser", "mobile", "cloud", "web-based", "audit", "compliance", "sla",
    "maintenance", "response time", "encryption", "access control",
)
_CONSTRAINT = ("not later than", "must not", "shall not", "budget", "deadline", "maximum", "minimum")


def _classify(statement: str) -> tuple[RequirementKind, Priority, float, tuple[str, ...]]:
    lower = statement.lower()
    reasons: list[str] = []
    if any(term in lower for term in _CONSTRAINT):
        kind = RequirementKind.CONSTRAINT
    elif any(term in lower for term in _NON_FUNCTIONAL):
        kind = RequirementKind.NON_FUNCTIONAL
    else:
        kind = RequirementKind.FUNCTIONAL

    if re.search(r"\b(?:shall|must|required)\b", lower):
        priority = Priority.MUST
    elif re.search(r"\bshould\b", lower):
        priority = Priority.SHOULD
    else:
        priority = Priority.COULD

    score = 0.15
    if not _MODAL.search(statement) and not _ACTION.search(statement):
        score += 0.25
        reasons.append("no explicit obligation or action verb detected")
    for term in _VAGUE:
        if term in lower:
            score += 0.15
            reasons.append(f"vague phrase: {term}")
    if re.search(r"\b(?:and|or)\b", lower):
        score += 0.1
        reasons.append("statement may contain multiple obligations")
    if not re.search(r"\b(?:when|if|within|at least|no more than|equal|equals|must be|shall be)\b", lower):
        score += 0.1
        reasons.append("no explicit condition or measurable threshold detected")
    return kind, priority, min(score, 1.0), tuple(reasons)


def extract_tor_text(source_text: str, source_name: str) -> TORExtractionDraft:
    """Extract candidate requirements deterministically; every item remains unapproved."""
    if not source_name.strip():
        raise ValueError("source_name must be non-empty")
    if not source_text.strip():
        raise ValueError("TOR source text must be non-empty")

    source_hash = hashlib.sha256(source_text.encode("utf-8")).hexdigest()
    lines = source_text.splitlines()
    section: str | None = None
    in_requirement_section = False
    candidates: list[TORCandidate] = []
    seen: dict[str, int] = {}

    for line_number, raw in enumerate(lines, start=1):
        stripped = raw.strip()
        if not stripped or stripped.startswith(">"):
            continue
        heading_text = re.sub(r"^#{1,6}\s*", "", stripped)
        if _HEADING.match(heading_text):
            section = heading_text.strip(" .:")
            in_requirement_section = bool(re.search(
                r"requirement|scope|objective|function|feature|technical|security|"
                r"report|support|service|acceptance|deliverable|integration|"
                r"performance|compliance|application|budget|maintenance|system|"
                r"processing|management|self service|pay slip",
                section,
                re.I,
            ))
            continue

        bullet = _BULLET.match(raw)
        if bullet:
            statement = bullet.group(1).strip()
            candidate_line = in_requirement_section or bool(_MODAL.search(statement))
        else:
            statement = stripped
            candidate_line = bool(_MODAL.search(statement)) or (
                in_requirement_section and bool(_ACTION.search(statement)) and not statement.endswith(":")
            )
        if not candidate_line or not statement or statement.endswith(":"):
            continue

        kind, priority, ambiguity, reasons = _classify(statement)
        normalized = re.sub(r"\W+", " ", statement.lower()).strip()
        seen[normalized] = seen.get(normalized, 0) + 1
        if seen[normalized] > 1:
            reasons = (*reasons, "duplicate or repeated requirement statement")
            ambiguity = min(1.0, ambiguity + 0.15)

        stable_material = f"{source_hash}:{line_number}:{statement}"
        requirement_id = "tor-" + hashlib.sha256(stable_material.encode("utf-8")).hexdigest()[:16]
        candidates.append(TORCandidate(
            requirement_id=requirement_id,
            statement=statement,
            proposed_kind=kind,
            proposed_priority=priority,
            ambiguity_score=ambiguity,
            ambiguity_reasons=reasons,
            section=section,
            source_ref=f"{source_name}#L{line_number}-L{line_number}",
            source_start_line=line_number,
            source_end_line=line_number,
        ))

    if not candidates:
        raise ValueError("no requirement candidates found; provide a clearer TOR or explicit obligation statements")

    return TORExtractionDraft(
        source_name=source_name,
        source_sha256=source_hash,
        source_text=source_text,
        candidates=tuple(candidates),
    )
