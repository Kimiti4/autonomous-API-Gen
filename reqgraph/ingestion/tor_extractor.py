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
from typing import Mapping

from pydantic import BaseModel, ConfigDict, Field

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
    """Explicit human decision required before a draft enters RequirementGraph."""
    model_config = ConfigDict(frozen=True, extra="forbid")
    reviewer_id: str = Field(min_length=1)
    approval_ref: str = Field(min_length=1)
    acceptance_criteria: tuple[str, ...] = Field(min_length=1)
    selected_kind: RequirementKind | None = None
    selected_priority: Priority | None = None
    resolution_ref: str | None = None


class TORExtractionDraft(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    source_name: str = Field(min_length=1)
    source_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    schema_version: str = "1.0"
    candidates: tuple[TORCandidate, ...] = ()

    def approve(
        self,
        approvals: Mapping[str, HumanApproval],
    ) -> RequirementGraph:
        """Build a validated graph only when every extracted item is approved."""
        candidate_ids = {candidate.requirement_id for candidate in self.candidates}
        missing = sorted(candidate_ids - set(approvals))
        extra = sorted(set(approvals) - candidate_ids)
        if missing or extra:
            raise ValueError(
                f"approval set must match extracted candidates; missing={missing}, extra={extra}"
            )

        nodes: dict[str, RequirementNode] = {}
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
            nodes[candidate.requirement_id] = RequirementNode(
                id=candidate.requirement_id,
                kind=kind,
                statement=candidate.statement,
                priority=priority,
                acceptance_criteria=approval.acceptance_criteria,
                ambiguity_score=candidate.ambiguity_score,
                resolution_ref=approval.resolution_ref,
                source_refs=(candidate.source_ref,),
                properties={
                    "source_name": self.source_name,
                    "source_sha256": self.source_sha256,
                    "source_start_line": candidate.source_start_line,
                    "source_end_line": candidate.source_end_line,
                    "section": candidate.section or "",
                    "ambiguity_reasons": list(candidate.ambiguity_reasons),
                    "review_status": ReviewStatus.APPROVED.value,
                    "reviewer_id": approval.reviewer_id,
                    "approval_ref": approval.approval_ref,
                },
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
    r"distribute|access|update|download|allocate|record|retain|demonstrate)\b",
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
        if not stripped:
            continue
        if _HEADING.match(stripped):
            section = stripped.strip(" .:")
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

    return TORExtractionDraft(
        source_name=source_name,
        source_sha256=source_hash,
        candidates=tuple(candidates),
    )
