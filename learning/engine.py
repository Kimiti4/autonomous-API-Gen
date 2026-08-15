"""
Continuous Learning Engine.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .analyzers import (
    CostAnalyzer,
    CustomerFeedbackAnalyzer,
    IncidentAnalyzer,
    PerformanceAnalyzer,
    SecurityLearningAnalyzer,
)
from .feedback_compiler import ArchitectureFeedbackCompiler
from .models import (
    ArchitectureFeedbackBundle,
    FitnessUpdate,
    LearningInsight,
    LearningPolicy,
    LearningRecommendation,
    LearningSignal,
)
from .pipeline import SignalPipeline
from .recommendations import FitnessUpdater, LearningRecommendationEngine


class ContinuousLearningEngine:
    """Coordinates continuous learning."""

    def __init__(self, policy: LearningPolicy | None = None) -> None:
        self.policy = policy or LearningPolicy()

        self.pipeline = SignalPipeline(self.policy)

        self.analyzers = [
            IncidentAnalyzer(),
            PerformanceAnalyzer(),
            CostAnalyzer(),
            SecurityLearningAnalyzer(),
            CustomerFeedbackAnalyzer(),
        ]

        self.recommendation_engine = LearningRecommendationEngine(self.policy)
        self.fitness_updater = FitnessUpdater()
        self.feedback_compiler = ArchitectureFeedbackCompiler()

        self.insights: Dict[str, LearningInsight] = {}
        self.recommendations: Dict[str, LearningRecommendation] = {}
        self.fitness_updates: Dict[str, FitnessUpdate] = {}
        self.bundles: Dict[str, ArchitectureFeedbackBundle] = {}

    def ingest_signal(self, signal: LearningSignal) -> LearningSignal:
        return self.pipeline.ingest(signal)

    def ingest_batch(self, signals: List[LearningSignal]) -> int:
        return self.pipeline.ingest_batch(signals)

    def analyze(
        self,
        subject_ref: Optional[str] = None,
    ) -> List[LearningInsight]:
        signals = self.pipeline.query(subject_ref=subject_ref)

        new_insights: List[LearningInsight] = []

        for analyzer in self.analyzers:
            insights = analyzer.analyze(signals, self.policy)

            for insight in insights:
                if insight.id not in self.insights:
                    self.insights[insight.id] = insight
                    new_insights.append(insight)

        all_insights = list(self.insights.values())

        recommendations = self.recommendation_engine.from_insights(all_insights)

        for recommendation in recommendations:
            self.recommendations[recommendation.id] = recommendation

        fitness_updates = self.fitness_updater.from_insights(all_insights)

        for update in fitness_updates:
            self.fitness_updates[update.id] = update

        return new_insights

    def compile_feedback(
        self,
        scope: str = "platform",
        subject_ref: Optional[str] = None,
    ) -> ArchitectureFeedbackBundle:
        if not self.insights:
            self.analyze(subject_ref=subject_ref)

        insights = list(self.insights.values())

        if subject_ref:
            insights = [
                insight
                for insight in insights
                if subject_ref in insight.affected_subjects
            ]

        recommendations = list(self.recommendations.values())

        if subject_ref:
            recommendations = [
                recommendation
                for recommendation in recommendations
                if recommendation.subject_ref == subject_ref
            ]

        fitness_updates = list(self.fitness_updates.values())

        if subject_ref:
            fitness_updates = [
                update
                for update in fitness_updates
                if update.subject_ref == subject_ref
            ]

        bundle = self.feedback_compiler.compile(
            scope=scope,
            insights=insights,
            recommendations=recommendations,
            fitness_updates=fitness_updates,
        )

        self.bundles[bundle.id] = bundle

        return bundle

    def report(self) -> Dict:
        return {
            "signal_count": len(self.pipeline.signals),
            "insight_count": len(self.insights),
            "recommendation_count": len(self.recommendations),
            "fitness_update_count": len(self.fitness_updates),
            "bundle_count": len(self.bundles),
        }
