import pytest

from constitutional_architecture.core.ckb.heuristics import (
    HeuristicAdjustmentStore,
)
from constitutional_architecture.core.learning.ckb_updater import CKBUpdater
from constitutional_architecture.core.learning.empirical_fitness import (
    EmpiricalFitnessCalculator,
)
from constitutional_architecture.core.learning.telemetry_ingestor import (
    GenomeTelemetryProfile, TelemetryIngestor,
)
from constitutional_architecture.core.models.intent import QualityAttribute


class TestTelemetryWatermarkExtraction:
    def test_watermark_extraction_and_aggregation(self):
        ingestor = TelemetryIngestor()

        trace_attrs = {
            "evolution.genome_id": "gen_99",
            "evolution.generation": 42,
            "evolution.architecture_style": "microservices",
        }

        ingestor.ingest_trace(trace_attrs, latency_ms=150.0, is_error=False)
        ingestor.ingest_trace(trace_attrs, latency_ms=800.0, is_error=True)

        profile = ingestor.get_empirical_data("gen_99")
        assert profile is not None
        assert profile.sample_size == 2
        assert profile.p99_latency_ms == 800.0
        assert profile.error_rate_percent == 50.0
        assert profile.generation == 42
        assert profile.architecture_style == "microservices"

    def test_unwatermarked_telemetry_ignored(self):
        ingestor = TelemetryIngestor()
        ingestor.ingest_trace({"user_id": "legacy"}, latency_ms=5.0,
                              is_error=False)
        assert ingestor.observed_genomes == 0

    def test_cost_and_mttr_ingestion_from_infra_tags(self):
        ingestor = TelemetryIngestor()
        ingestor.ingest_trace(
            {"evolution.genome_id": "gen_7"}, latency_ms=10.0, is_error=False)
        ingestor.ingest_infrastructure_cost("gen_7", 420.0)
        ingestor.ingest_mttr("gen_7", 300.0)
        profile = ingestor.get_empirical_data("gen_7")
        assert profile.monthly_infrastructure_cost_usd == 420.0
        assert profile.mttr_seconds == 300.0


class TestEmpiricalParetoScoring:
    def test_empirical_pareto_scoring(self):
        calc = EmpiricalFitnessCalculator()
        profile = GenomeTelemetryProfile(
            genome_id="gen_99", generation=42, architecture_style="microservices",
            p99_latency_ms=200.0,
            error_rate_percent=0.1,
            monthly_infrastructure_cost_usd=800.0,
            mttr_seconds=300.0,
        )

        scores = calc.calculate_real_world_fitness(profile)

        assert scores[QualityAttribute.PERFORMANCE] > 0.7
        assert scores[QualityAttribute.RELIABILITY] > 0.9
        assert scores[QualityAttribute.COST_EFFICIENCY] < 0.3
        assert scores[QualityAttribute.MAINTAINABILITY] > 0.8

    def test_pareto_dimensions_are_distinct(self):
        """A cheap-but-unreliable architecture is not rewarded overall."""
        calc = EmpiricalFitnessCalculator()
        cheap_unreliable = GenomeTelemetryProfile(
            genome_id="g1", generation=1, architecture_style="monolithic",
            p99_latency_ms=900.0, error_rate_percent=4.9,
            monthly_infrastructure_cost_usd=50.0, mttr_seconds=3500.0,
        )
        scores = calc.calculate_real_world_fitness(cheap_unreliable)
        assert scores[QualityAttribute.COST_EFFICIENCY] > 0.9
        assert scores[QualityAttribute.RELIABILITY] < 0.05


class TestCKBUpdater:
    def test_requires_statistical_significance(self):
        class MockCKB:
            def __init__(self):
                self.calls = []

            def adjust_heuristic(self, pattern, attr, direction, rate):
                self.calls.append((pattern, attr, direction, rate))

        updater = CKBUpdater(MockCKB())
        profile = GenomeTelemetryProfile(
            genome_id="gen_99", generation=42, architecture_style="microservices",
            p99_latency_ms=5000.0, error_rate_percent=10.0, sample_size=5,
        )
        predicted = {QualityAttribute.PERFORMANCE: 0.9}

        result = updater.evaluate_and_learn(profile, predicted)
        assert result is None  # silently ignored below MIN_SAMPLE_SIZE
        assert updater.ckb.calls == []

    def test_penalizes_underperforming_pattern(self):
        store = HeuristicAdjustmentStore()
        updater = CKBUpdater(store)
        profile = GenomeTelemetryProfile(
            genome_id="gen_99", generation=42,
            architecture_style="microservices",
            p99_latency_ms=5000.0, error_rate_percent=10.0, sample_size=60,
        )
        predicted = {QualityAttribute.PERFORMANCE: 0.9,
                     QualityAttribute.RELIABILITY: 0.9,
                     QualityAttribute.COST_EFFICIENCY: 0.5,
                     QualityAttribute.MAINTAINABILITY: 0.5}

        summary = updater.evaluate_and_learn(profile, predicted)
        assert summary is not None
        assert summary["penalized"]
        assert store.get_delta("microservices",
                               QualityAttribute.PERFORMANCE) < 0.0

    def test_rewards_overperforming_pattern(self):
        store = HeuristicAdjustmentStore()
        updater = CKBUpdater(store)
        profile = GenomeTelemetryProfile(
            genome_id="gen_7", generation=3,
            architecture_style="event_driven",
            p99_latency_ms=20.0, error_rate_percent=0.0,
            monthly_infrastructure_cost_usd=80.0, mttr_seconds=60.0,
            sample_size=80,
        )
        predicted = {QualityAttribute.PERFORMANCE: 0.5,
                     QualityAttribute.RELIABILITY: 0.5,
                     QualityAttribute.COST_EFFICIENCY: 0.5,
                     QualityAttribute.MAINTAINABILITY: 0.5}

        summary = updater.evaluate_and_learn(profile, predicted)
        assert summary is not None
        assert summary["rewarded"]
        assert store.get_delta("event_driven",
                               QualityAttribute.PERFORMANCE) > 0.0

    def test_learning_rate_is_bounded(self):
        """Repeated adjustments saturate; no catastrophic forgetting."""
        store = HeuristicAdjustmentStore()
        updater = CKBUpdater(store)
        profile = GenomeTelemetryProfile(
            genome_id="g", generation=1, architecture_style="bad",
            p99_latency_ms=9000.0, error_rate_percent=10.0, sample_size=60,
        )
        predicted = {QualityAttribute.PERFORMANCE: 0.9,
                     QualityAttribute.RELIABILITY: 0.9,
                     QualityAttribute.COST_EFFICIENCY: 0.5,
                     QualityAttribute.MAINTAINABILITY: 0.5}
        for _ in range(50):
            updater.evaluate_and_learn(profile, predicted)
        delta = store.get_delta("bad", QualityAttribute.PERFORMANCE)
        assert delta < 0.0
        assert delta >= -0.5
