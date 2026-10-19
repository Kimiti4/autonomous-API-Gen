"""Controlled, provenance-preserving TOR extraction.

This module segments prose and identifies candidate obligations; it does not
invent acceptance criteria, tax rates, formulas, routes, or architecture. Every
candidate requires an explicit review decision before it can enter the
authoritative RequirementGraph and ISR path.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
from typing import Mapping, Sequence

from genesis.mapper import GenesisResult, ReferenceDeterministicMapper
from isr.core.identity import Provenance
from isr.core.revision import ISRRevision
from reqgraph.core.graph import (
    Priority,
    RequirementGraph,
    RequirementKind,
    RequirementNode,
)
from reqgraph.core.invariants import validate_requirement_graph


EXTRACTION_VERSION = "controlled-tor-extraction/1.0"
_NORMATIVE = re.compile(r"\b(shall|must|required to|is required|should|will be able to|should be able to)\b", re.I)
_EXPLICIT_ID = re.compile(r"\b(?:REQ|TOR|NFR|FR|SEC|OPS)[-_][A-Z0-9][A-Z0-9_-]*\b", re.I)
_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$")
_NUMBERED_HEADING = re.compile(r"^\s*\d+(?:\.\d+)*\.?\s+([A-Z][A-Z0-9 /&()_-]{2,})\s*$")
_BULLET = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+|[a-zA-Z][.)]\s+)(.+?)\s*$")


@dataclass(frozen=True)
class TORCandidate:
    candidate_id: str
    statement: str
    section: str
    source_ref: str
    source_sha256: str
    line_start: int
    line_end: int
    explicit_id: str | None
    candidate_kind: RequirementKind | None
    priority: Priority
    ambiguity_score: float
    extraction_rule: str
    review_status: str = "pending_review"
    review_findings: tuple[str, ...] = ()


@dataclass(frozen=True)
class TORExtraction:
    source_id: str
    source_sha256: str
    extraction_version: str
    candidates: tuple[TORCandidate, ...]
    ignored_context: tuple[dict[str, object], ...]


@dataclass(frozen=True)
class RequirementReview:
    candidate_id: str
    kind: RequirementKind
    priority: Priority
    acceptance_criteria: tuple[str, ...]
    ambiguity_score: float = 0.0
    resolution_ref: str | None = None
    approved_by: str = ""


@dataclass(frozen=True)
class TORMappingResult:
    requirement_graph: RequirementGraph
    genesis: GenesisResult
    revision: ISRRevision


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _kind(text: str) -> tuple[RequirementKind | None, str]:
    lower = text.lower()
    if any(term in lower for term in ("statutory", "legislation", "tax law", "compliance", "security", "backup", "recovery", "audit trail", "role-based", "access control")):
        return RequirementKind.CONSTRAINT, "explicit-domain-or-governance-keyword"
    if any(term in lower for term in ("performance", "availability", "response time", "web-based", "cloud-hosted", "mobile access", "compatible with", "data backup")):
        return RequirementKind.NON_FUNCTIONAL, "explicit-quality-attribute-keyword"
    if _NORMATIVE.search(text):
        return RequirementKind.FUNCTIONAL, "explicit-normative-modal"
    if any(term in lower for term in ("employees should be able to", "vendor shall", "vendor should", "proposal should")):
        return RequirementKind.STAKEHOLDER, "explicit-stakeholder-obligation"
    return None, "unclassified-needs-human-review"


def _priority(text: str) -> Priority:
    lower = text.lower()
    if re.search(r"\b(must|shall|required|mandatory)\b", lower):
        return Priority.MUST
    if re.search(r"\bshould\b", lower):
        return Priority.SHOULD
    return Priority.COULD


def _segment(text: str) -> list[tuple[str, str, int, int, str]]:
    """Return (section, statement, start line, end line, segmentation rule)."""
    section = "Document"
    paragraph: list[tuple[int, str]] = []
    results: list[tuple[str, str, int, int, str]] = []

    def flush() -> None:
        nonlocal paragraph
        if not paragraph:
            return
        raw = _normalise(" ".join(line for _, line in paragraph))
        start, end = paragraph[0][0], paragraph[-1][0]
        if raw:
            # Split only when each resulting sentence remains independently
            # normative; otherwise preserve the full source paragraph.
            sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", raw)
            normative = [sentence.strip() for sentence in sentences if sentence.strip()]
            if len(normative) > 1 and all(_NORMATIVE.search(s) for s in normative):
                for sentence in normative:
                    results.append((section, sentence, start, end, "normative-sentence"))
            else:
                results.append((section, raw, start, end, "paragraph"))
        paragraph = []

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            flush()
            continue
        heading = _HEADING.match(raw_line)
        numbered_heading = _NUMBERED_HEADING.match(raw_line)
        if heading or numbered_heading:
            flush()
            section = _normalise((heading or numbered_heading).group(1))
            continue
        bullet = _BULLET.match(raw_line)
        if bullet:
            flush()
            results.append((section, _normalise(bullet.group(1)), line_number, line_number, "list-item"))
            continue
        paragraph.append((line_number, line))
    flush()
    return results


def extract_tor(text: str, source_id: str) -> TORExtraction:
    """Extract candidates with exact source locations; never auto-approve them."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("TOR text must be a non-empty string")
    if not source_id.strip():
        raise ValueError("source_id must be non-empty")
    source_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    candidates: list[TORCandidate] = []
    ignored: list[dict[str, object]] = []

    for section, statement, start, end, segmentation_rule in _segment(text):
        if len(statement) < 12:
            ignored.append({"section": section, "line_start": start, "text": statement, "reason": "too-short-context"})
            continue
        normative = bool(_NORMATIVE.search(statement))
        has_list_action = segmentation_rule == "list-item" and re.search(
            r"\b(manage|support|generate|provide|maintain|allow|ensure|automate|integrate|view|update|download|apply|include|allocate|process)\b",
            statement,
            re.I,
        )
        if not normative and not has_list_action and segmentation_rule != "list-item":
            ignored.append({
                "section": section,
                "line_start": start,
                "line_end": end,
                "text": statement,
                "reason": "context-not-explicit-obligation",
            })
            continue

        candidate_kind, kind_rule = _kind(statement)
        explicit = _EXPLICIT_ID.search(statement)
        identity = "\n".join((source_hash, section, str(start), str(end), statement))
        candidate_id = f"torreq:{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:20]}"
        findings: list[str] = []
        if candidate_kind is None:
            findings.append("requirement kind is unresolved")
        if not normative:
            findings.append("list item lacks an explicit normative modal")
        if not re.search(r"\b(test|verify|confirm|acceptance criteria|given .+ when .+ then)\b", statement, re.I):
            findings.append("no explicit acceptance oracle was extracted")
        candidates.append(TORCandidate(
            candidate_id=candidate_id,
            statement=statement,
            section=section,
            source_ref=f"{source_id}#L{start}-L{end}",
            source_sha256=source_hash,
            line_start=start,
            line_end=end,
            explicit_id=explicit.group(0) if explicit else None,
            candidate_kind=candidate_kind,
            priority=_priority(statement),
            ambiguity_score=0.0 if normative and candidate_kind is not None else 0.65,
            extraction_rule=f"{segmentation_rule}+{kind_rule}",
            review_findings=tuple(findings),
        ))

    return TORExtraction(
        source_id=source_id,
        source_sha256=source_hash,
        extraction_version=EXTRACTION_VERSION,
        candidates=tuple(candidates),
        ignored_context=tuple(ignored),
    )


def reviewed_requirements_to_graph(
    extraction: TORExtraction,
    reviews: Mapping[str, RequirementReview],
    *,
    schema_version: str = "1.0",
) -> RequirementGraph:
    """Only explicitly reviewed candidates can enter the authoritative graph."""
    candidates = {candidate.candidate_id: candidate for candidate in extraction.candidates}
    unknown = sorted(set(reviews) - set(candidates))
    if unknown:
        raise ValueError(f"review refers to unknown TOR candidates: {unknown}")
    nodes: dict[str, RequirementNode] = {}
    for candidate_id, review in sorted(reviews.items()):
        if candidate_id != review.candidate_id:
            raise ValueError(f"review key/id mismatch for {candidate_id!r}")
        candidate = candidates[candidate_id]
        if not review.approved_by.strip():
            raise ValueError(f"candidate {candidate_id!r} requires an explicit reviewer")
        if review.kind is RequirementKind.FUNCTIONAL and not review.acceptance_criteria:
            raise ValueError(f"functional candidate {candidate_id!r} needs acceptance criteria")
        if review.ambiguity_score > 0.5 and not review.resolution_ref:
            raise ValueError(f"ambiguous candidate {candidate_id!r} needs a resolution reference")
        node_id = candidate.explicit_id or candidate.candidate_id
        if node_id in nodes:
            raise ValueError(f"duplicate reviewed requirement ID: {node_id}")
        nodes[node_id] = RequirementNode(
            id=node_id,
            kind=review.kind,
            statement=candidate.statement,
            priority=review.priority,
            acceptance_criteria=review.acceptance_criteria,
            ambiguity_score=review.ambiguity_score,
            resolution_ref=review.resolution_ref,
            source_refs=(
                candidate.source_ref,
                f"sha256:{candidate.source_sha256}",
            ),
            properties={
                "tor_extraction_version": extraction.extraction_version,
                "source_id": extraction.source_id,
                "source_section": candidate.section,
                "source_line_start": candidate.line_start,
                "source_line_end": candidate.line_end,
                "source_text_sha256": candidate.source_sha256,
                "candidate_id": candidate.candidate_id,
                "review_status": "approved",
                "reviewer": review.approved_by,
                "extraction_rule": candidate.extraction_rule,
            },
        )
    graph = RequirementGraph(schema_version=schema_version, nodes=nodes, edges={})
    validate_requirement_graph(graph)
    return graph


def map_reviewed_tor_to_isr(
    extraction: TORExtraction,
    reviews: Mapping[str, RequirementReview],
    *,
    system_id: str,
    revision_id: str,
    created_at: str,
    mapping_spec_version: str = "tor-genesis-1.0",
) -> TORMappingResult:
    """Use the canonical RequirementGraph -> Genesis -> ISR path."""
    requirement_graph = reviewed_requirements_to_graph(extraction, reviews)
    genesis = ReferenceDeterministicMapper().map(requirement_graph, mapping_spec_version)
    revision = ISRRevision.create(
        system_id=system_id,
        revision_id=revision_id,
        schema_version="1.0",
        graph=genesis.graph,
        provenance=Provenance(
            created_by="controlled_tor_extraction",
            created_at=created_at,
            requirement_refs=tuple(sorted(requirement_graph.nodes)),
        ),
    )
    return TORMappingResult(requirement_graph, genesis, revision)
