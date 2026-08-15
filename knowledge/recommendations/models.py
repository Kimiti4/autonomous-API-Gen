"""
Recommendation analytics models.
"""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


Severity = Literal[
    "LOW",
    "MEDIUM",
    "HIGH",
    "CRITICAL",
]


class RecommendationRecord(BaseModel):
    """A recommendation to be analyzed."""

    id: str
    title: str
    description: str = ""

    recommendation_type: str = "GENERAL"
    suggested_action: str = ""

    target_entity_id: Optional[str] = None

    source_entity_ids: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)

    sensitivity: str = "INTERNAL"

    created_at: Optional[str] = None

    contradicts: list[str] = Field(default_factory=list)


class EvidenceSignal(BaseModel):
    """Evidence signal correlated with one or more recommendations."""

    signal_type: str
    source_id: str

    severity: Severity = "MEDIUM"
    confidence: float = Field(default=0.70, ge=0.0, le=1.0)

    observed_at: Optional[str] = None
    description: str = ""

    related_recommendation_ids: list[str] = Field(default_factory=list)


class RecommendationAnalyticsRequest(BaseModel):
    """Request to analyze recommendations."""

    recommendations: list[RecommendationRecord]
    signals: list[EvidenceSignal] = Field(default_factory=list)

    duplicate_threshold: float = Field(default=0.65, ge=0.0, le=1.0)
    max_results: int = Field(default=50, ge=1, le=500)

    include_packet: bool = True
    redact_sensitive: bool = True

    context: dict[str, Any] = Field(default_factory=dict)


class RankedRecommendation(BaseModel):
    """A recommendation after analytics scoring."""

    recommendation: RecommendationRecord

    evidence_score: float
    impact_score: float
    urgency_score: float
    priority_score: float
    risk_score: float

    priority_level: str
    risk_level: str

    matched_signals: list[EvidenceSignal] = Field(default_factory=list)
    rationale: str = ""


class DuplicateCluster(BaseModel):
    """A cluster of likely duplicate recommendations."""

    cluster_id: str
    recommendation_ids: list[str] = Field(default_factory=list)
    similarity: float
    reason: str


class ConflictRecord(BaseModel):
    """A conflict between recommendations."""

    conflict_id: str
    recommendation_ids: list[str] = Field(default_factory=list)
    conflict_type: str
    severity: Severity
    reason: str


class RecommendationPacket(BaseModel):
    """Governance-ready recommendation packet."""

    packet_id: str
    created_at: str

    context: dict[str, Any] = Field(default_factory=dict)

    ranked_recommendations: list[RankedRecommendation] = Field(default_factory=list)
    duplicate_clusters: list[DuplicateCluster] = Field(default_factory=list)
    conflicts: list[ConflictRecord] = Field(default_factory=list)

    governance_status: str = "DRAFT"

    submission_constraints: list[str] = Field(default_factory=list)


class RecommendationAnalyticsMetadata(BaseModel):
    """Metadata for recommendation analytics."""

    request_id: str
    total_recommendations: int
    analyzed_recommendations: int
    excluded_sensitive_count: int
    duplicate_cluster_count: int
    conflict_count: int
    generated_at: str


class RecommendationAnalyticsResult(BaseModel):
    """Recommendation analytics result."""

    metadata: RecommendationAnalyticsMetadata
    ranked_recommendations: list[RankedRecommendation] = Field(default_factory=list)
    duplicate_clusters: list[DuplicateCluster] = Field(default_factory=list)
    conflicts: list[ConflictRecord] = Field(default_factory=list)
    packet: Optional[RecommendationPacket] = None
