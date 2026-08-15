import pytest

from constitutional_architecture.core.ckb.archetype_registry import (
    ArchetypeRegistry,
)
from constitutional_architecture.core.learning.telemetry_ingestor import (
    GenomeTelemetryProfile,
)
from constitutional_architecture.core.macro_evolution.fleet_analyzer import (
    FleetAnalyzer,
)
from constitutional_architecture.core.macro_evolution.synthesizer import (
    ArchetypeSynthesizer,
)
from constitutional_architecture.core.models.intent import QualityAttribute


class MockCKB:
    def __init__(self):
        self.registered_archetypes = {}

    def register_archetype(self, name, base_genes, empirical_weights):
        self.registered_archetypes[name] = {
            "genes": base_genes, "weights": empirical_weights}


def _fleet(size=15, style="EventDriven_Edge", latency_ms=20.0):
    return [
        GenomeTelemetryProfile(
            genome_id=f"g_{i}", generation=10, architecture_style=style,
            p99_latency_ms=latency_ms,
            error_rate_percent=0.0,
            monthly_infrastructure_cost_usd=100.0,
            mttr_seconds=60.0,
        )
        for i in range(size)
    ]


class TestFleetAnalyzer:
    def test_fleet_analyzer_detects_emergent_pattern(self):
        analyzer = FleetAnalyzer()
        fleet = _fleet()
        baseline_ckb_scores = {
            "EventDriven_Edge": {QualityAttribute.PERFORMANCE: 0.50}}

        patterns = analyzer.discover_emergent_patterns(fleet, baseline_ckb_scores)

        assert len(patterns) > 0
        assert patterns[0]["topology_signature"] == "EventDriven_Edge"
        assert patterns[0]["attribute"] == QualityAttribute.PERFORMANCE
        assert patterns[0]["deviation"] > 0.25

    def test_sample_size_gate_blocks_noise(self):
        analyzer = FleetAnalyzer()
        fleet = _fleet(size=5)  # below MIN_DEPLOYMENTS of 10
        patterns = analyzer.discover_emergent_patterns(
            fleet, {"EventDriven_Edge": {QualityAttribute.PERFORMANCE: 0.5}})
        assert patterns == []

    def test_no_deviation_no_pattern(self):
        analyzer = FleetAnalyzer()
        fleet = _fleet(size=15, latency_ms=600.0)  # empirical ~0.4
        patterns = analyzer.discover_emergent_patterns(
            fleet, {"EventDriven_Edge": {QualityAttribute.PERFORMANCE: 0.8}})
        assert patterns == []


class TestArchetypeSynthesizer:
    def test_platform_mints_new_archetype_and_adr(self):
        ckb = MockCKB()
        synthesizer = ArchetypeSynthesizer(ckb)

        pattern_data = {
            "topology_signature": "EventDriven_Edge",
            "attribute": QualityAttribute.PERFORMANCE,
            "empirical_score": 0.98,
            "baseline_score": 0.50,
            "deviation": 0.48,
            "sample_size": 15,
        }

        adr = synthesizer.synthesize_new_archetype(pattern_data)

        assert "EMERGENT_EVENTDRIVEN_EDGE_PERFORMANCE" in ckb.registered_archetypes
        assert "Platform ADR: Minting New Archetype" in adr
        assert "Fleet Telemetry Anomaly Detection" in adr
        assert "EXPERIMENTAL" in adr

    def test_synthesizer_with_real_registry(self):
        registry = ArchetypeRegistry()
        synthesizer = ArchetypeSynthesizer(registry)
        pattern_data = {
            "topology_signature": "EdgeWasm",
            "attribute": QualityAttribute.PERFORMANCE,
            "empirical_score": 0.9,
            "baseline_score": 0.5,
            "deviation": 0.4,
            "sample_size": 25,
        }
        synthesizer.synthesize_new_archetype(pattern_data)
        assert "EMERGENT_EDGEWASM_PERFORMANCE" in registry.registered
        assert registry.is_experimental("EMERGENT_EDGEWASM_PERFORMANCE")
        weights = registry.registered["EMERGENT_EDGEWASM_PERFORMANCE"]["weights"]
        assert weights[QualityAttribute.PERFORMANCE.value] == 0.95

    def test_adr_documents_evidence(self):
        ckb = MockCKB()
        synthesizer = ArchetypeSynthesizer(ckb)
        pattern_data = {
            "topology_signature": "CQRS_MultiRegion",
            "attribute": QualityAttribute.RELIABILITY,
            "empirical_score": 0.97,
            "baseline_score": 0.7,
            "deviation": 0.27,
            "sample_size": 12,
        }
        adr = synthesizer.synthesize_new_archetype(pattern_data)
        assert "Across `12` independent production deployments" in adr
        assert "27.00%" in adr
        assert "reliability" in adr
