"""
Marketplace design engine.
"""

from __future__ import annotations

from typing import List

from .models import (
    DemandOpportunity,
    MarketplaceAutonomyPolicy,
    MarketplaceDesignProposal,
    MarketplaceFitnessReport,
    MarketplaceMetricSnapshot,
    ProposalType,
)


class MarketplaceDesignEngine:
    """Generates governed marketplace design proposals."""

    def __init__(self, policy: MarketplaceAutonomyPolicy) -> None:
        self.policy = policy

    def generate_proposals(
        self,
        snapshot: MarketplaceMetricSnapshot,
        fitness: MarketplaceFitnessReport,
        opportunities: List[DemandOpportunity],
    ) -> List[MarketplaceDesignProposal]:
        proposals: List[MarketplaceDesignProposal] = []

        if fitness.objectives.get("conversion_quality", 0.0) < 0.05:
            proposals.append(
                MarketplaceDesignProposal(
                    marketplace_id=snapshot.marketplace_id,
                    proposal_type=ProposalType.RANKING_POLICY,
                    title="Increase ranking weight for certification and tests",
                    rationale=(
                        "Conversion quality is low. Increase ranking weight for "
                        "certification, testing, and security quality."
                    ),
                    changes={
                        "ranking_weights": {
                            "certification_score": 0.30,
                            "test_score": 0.25,
                            "security_score": 0.20,
                        }
                    },
                    evidence_refs=[f"marketplace:{snapshot.marketplace_id}"],
                    fitness_impact={
                        "conversion_quality": 0.05,
                        "trust": 0.03,
                    },
                    governance_required=(
                        self.policy.require_human_approval_for_ranking_change
                    ),
                )
            )

        refund_rate_ok = fitness.constraints.get("refund_rate_ok", True)

        if not refund_rate_ok:
            proposals.append(
                MarketplaceDesignProposal(
                    marketplace_id=snapshot.marketplace_id,
                    proposal_type=ProposalType.CURATION_POLICY,
                    title="Tighten curation and refund controls",
                    rationale="Refund rate exceeds acceptable threshold.",
                    changes={
                        "require_certified_for_publication": True,
                        "require_rollback_plan": True,
                        "require_support_sla": True,
                    },
                    evidence_refs=[f"marketplace:{snapshot.marketplace_id}"],
                    fitness_impact={
                        "trust": 0.05,
                        "support_health": 0.03,
                    },
                    governance_required=(
                        self.policy.require_human_approval_for_curation_change
                    ),
                )
            )

        if opportunities:
            top_opportunity = opportunities[0]

            proposals.append(
                MarketplaceDesignProposal(
                    marketplace_id=snapshot.marketplace_id,
                    proposal_type=ProposalType.PRODUCT_PORTFOLIO,
                    title=(
                        f"Generate products for underserved category: "
                        f"{top_opportunity.category}"
                    ),
                    rationale=top_opportunity.recommendation,
                    changes={
                        "target_category": top_opportunity.category,
                        "demand_score": top_opportunity.demand_score,
                        "product_count": top_opportunity.product_count,
                    },
                    evidence_refs=top_opportunity.evidence_refs,
                    fitness_impact={
                        "liquidity": 0.04,
                        "conversion_quality": 0.02,
                    },
                    governance_required=True,
                )
            )

        if fitness.objectives.get("revenue_health", 0.0) < 0.3:
            proposals.append(
                MarketplaceDesignProposal(
                    marketplace_id=snapshot.marketplace_id,
                    proposal_type=ProposalType.PRICING_POLICY,
                    title="Run pricing experiment",
                    rationale=(
                        "Revenue health is low. Run a bounded pricing experiment "
                        "under governance guardrails."
                    ),
                    changes={
                        "experiment_type": "pricing",
                        "max_traffic_pct": self.policy.max_experiment_traffic_pct,
                    },
                    evidence_refs=[f"marketplace:{snapshot.marketplace_id}"],
                    fitness_impact={
                        "revenue_health": 0.05,
                    },
                    governance_required=(
                        self.policy.require_human_approval_for_fee_change
                    ),
                )
            )

        return proposals
