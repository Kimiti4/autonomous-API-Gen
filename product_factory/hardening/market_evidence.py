"""
Phase 24.2 — Market Research and Evidence Adapters.
"""

from __future__ import annotations

from typing import Dict, List

from ..utils import deterministic_id, utcnow
from .models import MarketEvidence, MarketEvidenceReport, MarketEvidenceSource


class MarketEvidenceEngine:
    """Collects and evaluates market evidence."""

    def __init__(self) -> None:
        self.sources: Dict[str, MarketEvidenceSource] = {}
        self.evidence: List[MarketEvidence] = []

    def register_source(self, source: MarketEvidenceSource) -> MarketEvidenceSource:
        self.sources[source.source_id] = source
        return source

    def ingest_evidence(self, evidence: MarketEvidence) -> MarketEvidence:
        source = self.sources.get(evidence.source_id)

        if source:
            adjusted_confidence = (
                evidence.confidence + source.reliability
            ) / 2.0
        else:
            adjusted_confidence = evidence.confidence * 0.7

        evidence.confidence = round(min(1.0, max(0.0, adjusted_confidence)), 4)

        if not evidence.id:
            evidence.id = deterministic_id(
                "market_evidence",
                {
                    "product_id": evidence.product_id,
                    "claim": evidence.claim,
                    "source_id": evidence.source_id,
                    "occurred_at": evidence.occurred_at,
                },
            )

        self.evidence.append(evidence)

        return evidence

    def report(self, product_id: str) -> MarketEvidenceReport:
        product_evidence = [
            evidence
            for evidence in self.evidence
            if evidence.product_id == product_id
        ]

        if not product_evidence:
            return MarketEvidenceReport(
                product_id=product_id,
                evidence_count=0,
                average_confidence=0.0,
                corroboration_score=0.0,
                overall_quality=0.0,
                claims=[],
                created_at=utcnow().isoformat(),
            )

        claims: Dict[str, set[str]] = {}

        total_confidence = 0.0

        for evidence in product_evidence:
            total_confidence += evidence.confidence

            claims.setdefault(evidence.claim, set()).add(evidence.source_id)

        average_confidence = total_confidence / len(product_evidence)

        corroborated_claims = sum(
            1
            for sources in claims.values()
            if len(sources) > 1
        )

        corroboration_score = (
            corroborated_claims / len(claims)
            if claims
            else 0.0
        )

        overall_quality = round(
            (0.7 * average_confidence) + (0.3 * corroboration_score),
            4,
        )

        return MarketEvidenceReport(
            product_id=product_id,
            evidence_count=len(product_evidence),
            average_confidence=round(average_confidence, 4),
            corroboration_score=round(corroboration_score, 4),
            overall_quality=overall_quality,
            claims=list(claims.keys()),
            created_at=utcnow().isoformat(),
        )
