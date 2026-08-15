"""Extraction -> RequirementGraph construction and pre-validation.

Single source of truth for turning an ExtractionOutput into a RequirementGraph
and for computing pre-validation issues. The compiler and tests reuse these
helpers, so there is no logic duplication and replay signatures stay stable.
"""

from __future__ import annotations

from pydantic import ValidationError

from tiannara.domain.models.requirement_graph import (
    EdgeKind,
    GraphProvenance,
    RequirementEdge,
    RequirementGraph,
    RequirementGraphValidationError,
    RequirementKind,
    RequirementNode,
)
from tiannara.domain.models.system_model import Priority
from tiannara.domain.services.canonical import sha256_hex
from tiannara.domain.services.graph_analysis import analyze

from .schemas import AssumptionSeed, ExtractionOutput


def graph_from_extraction(
    extraction: ExtractionOutput,
    assumptions: list[AssumptionSeed],
    provenance_tags: list[str],
    source_statement_hash: str,
) -> RequirementGraph:
    """Build a RequirementGraph from extraction seeds plus explicit assumptions.

    Raises RequirementGraphValidationError (or ValueError for bad enum strings)
    when the candidate is structurally invalid; callers convert that into
    pre-validation issues.
    """

    def _issue_messages(exc: ValidationError) -> list[str]:
        # Pull only the stable ``loc`` + ``msg``; the ``input`` field embeds
        # provenance tags (model_versions) which would otherwise leak call
        # signatures into the repair-request signature and break replay.
        messages: list[str] = []
        for err in exc.errors():
            loc = ".".join(str(part) for part in err.get("loc", []))
            msg = err.get("msg", "")
            if loc:
                messages.append(f"{loc}: {msg}")
            else:
                messages.append(msg)
        return messages

    nodes: list[RequirementNode] = []
    for seed in extraction.nodes:
        nodes.append(
            RequirementNode(
                id=seed.ref,
                kind=RequirementKind(seed.kind),
                statement=seed.statement,
                priority=Priority(seed.priority),
                acceptance_criteria=seed.acceptance_criteria,
                rationale=seed.rationale,
            )
        )
    for index, assumption in enumerate(assumptions, start=1):
        nodes.append(
            RequirementNode(
                id=f"asm-{index}",
                kind=RequirementKind.ASSUMPTION,
                statement=assumption.statement,
                priority=Priority.SHOULD,
                rationale=assumption.rationale,
            )
        )

    edges: list[RequirementEdge] = [
        RequirementEdge(
            source_id=seed.source_ref,
            target_id=seed.target_ref,
            kind=EdgeKind(seed.kind),
            rationale=seed.rationale,
        )
        for seed in extraction.edges
    ]

    graph_id = f"rg-{sha256_hex(source_statement_hash)[:16]}"
    provenance = GraphProvenance(
        origin="intent_compiler",
        source_statement_hash=source_statement_hash,
        model_versions=list(provenance_tags),
    )
    try:
        graph = RequirementGraph(
            graph_id=graph_id, nodes=nodes, edges=edges, provenance=provenance
        )
    except ValidationError as exc:
        if isinstance(exc, RequirementGraphValidationError):
            raise
        raise RequirementGraphValidationError(
            "; ".join(_issue_messages(exc))
        ) from exc
    return graph


def prevalidate(graph: RequirementGraph) -> list[str]:
    """Semantic pre-validation issues that should trigger repair.

    Authoritative requirement analysis remains the Evolution Engine's job;
    this only surfaces structural-soundness problems cheaply.
    """
    findings = analyze(graph)
    issues: list[str] = []
    for cycle in findings.cycles:
        issues.append("directed cycle: " + " -> ".join(cycle))
    for pair in findings.asymmetric_conflicts:
        issues.append(f"asymmetric conflict between '{pair[0]}' and '{pair[1]}'")
    return issues


def attempt_graph(
    extraction: ExtractionOutput,
    assumptions: list[AssumptionSeed],
    provenance_tags: list[str],
    source_statement_hash: str,
) -> tuple[RequirementGraph | None, list[str]]:
    """Return (graph, issues). graph is None when construction failed."""
    try:
        graph = graph_from_extraction(
            extraction, assumptions, provenance_tags, source_statement_hash
        )
    except (RequirementGraphValidationError, ValueError) as exc:
        return None, [str(exc)]
    return graph, prevalidate(graph)
