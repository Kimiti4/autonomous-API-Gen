"""
Autonomous marketplace design and economics engine.
"""

from __future__ import annotations

from typing import Dict, List

from .demand import DemandAnalyzer
from .design_engine import MarketplaceDesignEngine
from .economics import EconomicsEngine
from .experiments import ExperimentManager
from .fitness import MarketplaceFitnessEvaluator
from .fraud import FraudDetectionEngine
from .models import (
    ListingRankingContext,
    MarketplaceAutonomyPolicy,
    MarketplaceAutonomyReport,
    MarketplaceDesignProposal,
    MarketplaceMetricSnapshot,
    ProposalStatus,
)
from .ranking import RankingEngine


class MarketplaceAutonomyEngine:
    """Coordinates marketplace analysis, design proposals, and experiments."""

    def __init__(
        self,
        policy: MarketplaceAutonomyPolicy | None = None,
    ) -> None:
        self.policy = policy or MarketplaceAutonomyPolicy()

        self.fitness_evaluator = MarketplaceFitnessEvaluator(self.policy)
        self.demand_analyzer = DemandAnalyzer()
        self.design_engine = MarketplaceDesignEngine(self.policy)
        self.economics_engine = EconomicsEngine(self.policy)
        self.ranking_engine = RankingEngine(self.policy)
        self.fraud_engine = FraudDetectionEngine(self.policy)
        self.experiment_manager = ExperimentManager(self.policy)

        self.proposals: Dict[str, MarketplaceDesignProposal] = {}

    def analyze_marketplace(
        self,
        snapshot: MarketplaceMetricSnapshot,
        listings: List[ListingRankingContext] | None = None,
    ) -> MarketplaceAutonomyReport:
        fitness = self.fitness_evaluator.evaluate(snapshot)

        opportunities = self.demand_analyzer.analyze(snapshot)

        fraud_alerts = []

        if listings:
            for listing in listings:
                assessment = self.fraud_engine.assess_listing(listing)

                if assessment.fraud_score >= self.policy.fraud_score_alert_threshold:
                    fraud_alerts.append(assessment)

        proposals = self.design_engine.generate_proposals(
            snapshot=snapshot,
            fitness=fitness,
            opportunities=opportunities,
        )

        for proposal in proposals:
            self.proposals[proposal.id] = proposal

        return MarketplaceAutonomyReport(
            marketplace_id=snapshot.marketplace_id,
            fitness=fitness,
            opportunities=opportunities,
            fraud_alerts=fraud_alerts,
            proposals=proposals,
        )

    def submit_proposal_to_governance(
        self,
        proposal_id: str,
        approval_ref: str | None = None,
    ) -> MarketplaceDesignProposal:
        proposal = self.proposals.get(proposal_id)

        if not proposal:
            raise KeyError(f"Proposal not found: {proposal_id}")

        if proposal.governance_required and not approval_ref:
            proposal.status = ProposalStatus.PENDING_GOVERNANCE
        else:
            proposal.status = ProposalStatus.APPROVED
            proposal.approval_ref = approval_ref

        proposal.updated_at = __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        )

        return proposal

    def rank_listings(
        self,
        listings: List[ListingRankingContext],
    ):
        return self.ranking_engine.rank_listings(listings)
