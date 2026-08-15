"""RequirementGraph -- typed requirement structure inside the ISR.

Per the Constitution, requirement analysis is the first evolution stage and
the Evolution Engine operates exclusively on the ISR; the RequirementGraph
therefore lives inside the ISR payload, and the authoritative analysis is
performed by the evolution engine's requirement-analysis stage using the
pure operations in ``domain.services.graph_analysis``.

What is enforced here is only *structural* validity (fail-fast at boundaries):
unique node ids, no dangling edges, no duplicate edges. Semantic findings
(cycles, conflicts, coverage gaps) are analysis output produced by
``graph_analysis.analyze`` -- they are attached to ``analysis`` and never
block construction.
"""

from __future__ import annotations

import enum
import uuid

from pydantic import BaseModel, Field, model_validator

from ..services.canonical import canonical_hash
from .system_model import Priority


class RequirementKind(str, enum.Enum):
    FUNCTIONAL = "functional"
    QUALITY = "quality"
    CONSTRAINT = "constraint"
    COMPLIANCE = "compliance"
    INTEGRATION = "integration"
    DATA = "data"
    BUSINESS_RULE = "business_rule"
    ASSUMPTION = "assumption"
    UNCLASSIFIED = "unclassified"   # schema-evolution flag, never a crash


class VerificationMethod(str, enum.Enum):
    TEST = "test"
    ANALYSIS = "analysis"
    DEMONSTRATION = "demonstration"
    INSPECTION = "inspection"


class NodeProvenance(BaseModel):
    source: str = "unknown"        # "synthesized" | "human" | "imported" | ...
    taxonomy_version: str | None = None
    stratum: str | None = None
    seed: int | None = None
    created_by: str = "unknown"


class RequirementNode(BaseModel):
    id: str
    kind: RequirementKind
    statement: str = Field(min_length=1)
    priority: Priority = Priority.MUST
    acceptance_criteria: list[str] = Field(default_factory=list)
    verification_method: VerificationMethod = VerificationMethod.TEST
    rationale: str = ""
    provenance: NodeProvenance = Field(default_factory=NodeProvenance)


class EdgeKind(str, enum.Enum):
    REFINES = "refines"
    DEPENDS_ON = "depends_on"
    CONFLICTS_WITH = "conflicts_with"
    REALIZES = "realizes"
    CONSTRAINS = "constrains"
    DERIVES_FROM = "derives_from"


#: Edge kinds that form directed relations (cycle-relevant).
DIRECTED_EDGE_KINDS: frozenset[EdgeKind] = frozenset(
    {
        EdgeKind.REFINES,
        EdgeKind.DEPENDS_ON,
        EdgeKind.REALIZES,
        EdgeKind.CONSTRAINS,
        EdgeKind.DERIVES_FROM,
    }
)


class RequirementEdge(BaseModel):
    source_id: str
    target_id: str
    kind: EdgeKind
    rationale: str = ""


class GraphProvenance(BaseModel):
    origin: str = "unknown"
    source_statement_hash: str | None = None
    taxonomy_version: str | None = None
    stratum: str | None = None
    seed: int | None = None
    #: Every model call that touched this graph: "model@version:call-hash".
    model_versions: list[str] = Field(default_factory=list)


class RequirementGraphValidationError(ValueError):
    pass


class RequirementGraph(BaseModel):
    graph_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    nodes: list[RequirementNode] = Field(default_factory=list)
    edges: list[RequirementEdge] = Field(default_factory=list)
    provenance: GraphProvenance = Field(default_factory=GraphProvenance)
    #: Derived view. Excluded from content_hash: identical graphs must hash
    #: identically regardless of whether analysis has been attached.
    analysis: "AnalysisFindings | None" = None

    @model_validator(mode="after")
    def _structural_validation(self) -> "RequirementGraph":
        ids = [node.id for node in self.nodes]
        if len(ids) != len(set(ids)):
            duplicates = sorted({i for i in ids if ids.count(i) > 1})
            raise RequirementGraphValidationError(f"duplicate node ids: {duplicates}")
        node_ids = set(ids)
        seen_edges: set[tuple[str, str, EdgeKind]] = set()
        for edge in self.edges:
            if edge.source_id not in node_ids or edge.target_id not in node_ids:
                raise RequirementGraphValidationError(
                    f"dangling edge {edge.source_id} -> {edge.target_id}"
                    f" (kind={edge.kind})"
                )
            if edge.kind in DIRECTED_EDGE_KINDS and edge.source_id == edge.target_id:
                raise RequirementGraphValidationError(
                    f"self-loop on directed edge kind at node '{edge.source_id}'"
                )
            key = (edge.source_id, edge.target_id, edge.kind)
            if key in seen_edges:
                raise RequirementGraphValidationError(f"duplicate edge: {key}")
            seen_edges.add(key)
        return self

    def node_index(self) -> dict[str, "RequirementNode"]:
        return {node.id: node for node in self.nodes}

    def content_hash(self) -> str:
        dump = self.model_dump(mode="json", exclude={"analysis"})
        return canonical_hash(dump)


# --------------------------------------------------------------------------
# Analysis findings (produced by domain.services.graph_analysis)
# --------------------------------------------------------------------------

class GapFinding(BaseModel):
    node_id: str
    description: str


class CoverageReport(BaseModel):
    total_nodes: int
    by_kind: dict[str, int] = Field(default_factory=dict)
    by_priority: dict[str, int] = Field(default_factory=dict)
    isolated_must_nodes: list[str] = Field(default_factory=list)


class AnalysisFindings(BaseModel):
    cycles: list[list[str]] = Field(default_factory=list)
    orphan_nodes: list[str] = Field(default_factory=list)
    asymmetric_conflicts: list[list[str]] = Field(default_factory=list)
    coverage: "CoverageReport | None" = None

    @property
    def has_structural_problems(self) -> bool:
        return bool(self.cycles or self.asymmetric_conflicts)
