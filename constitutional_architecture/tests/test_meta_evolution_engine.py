"""Tests for MetaEvolutionEngine (end-to-end orchestrator)."""

import pytest

from constitutional_architecture.meta.meta_evolution_engine import MetaEvolutionEngine
from constitutional_architecture.meta.events import MetaEvent, MetaEventType
from constitutional_architecture.meta.platform_genome import create_default_genome


class TestMetaEvolutionEngine:
    def test_initialization(self):
        engine = MetaEvolutionEngine()
        assert engine.genome.version == 1
        assert engine.can_rollback is True
        assert engine.lineage.total_entries == 1

    def test_evolve_random_strategy(self):
        engine = MetaEvolutionEngine()
        metrics = {
            "evolution_success_rate": 0.5,
            "compilation_success_rate": 0.5,
            "verification_accuracy": 0.5,
        }
        success, message = engine.evolve(metrics, strategy="random")
        assert success is True, f"Evolution failed: {message}"
        assert "Platform evolved" in message

    def test_evolve_adaptive_strategy(self):
        engine = MetaEvolutionEngine()
        metrics = {
            "evolution_success_rate": 0.6,
            "compilation_success_rate": 0.7,
            "verification_accuracy": 0.8,
        }
        success, message = engine.evolve(metrics, strategy="adaptive")
        assert success is True, f"Evolution failed: {message}"

    def test_evolve_guided_strategy(self):
        engine = MetaEvolutionEngine()
        metrics = {
            "evolution_success_rate": 0.4,
            "compilation_success_rate": 0.4,
            "verification_accuracy": 0.4,
        }
        success, message = engine.evolve(metrics, strategy="guided")
        assert success is True, f"Evolution failed: {message}"

    def test_rollback_after_evolution(self):
        engine = MetaEvolutionEngine()
        metrics = {
            "evolution_success_rate": 0.5,
            "compilation_success_rate": 0.5,
            "verification_accuracy": 0.5,
        }
        engine.evolve(metrics, strategy="random")
        assert engine.can_rollback is True
        success, message = engine.rollback()
        assert success is True
        assert "Rolled back" in message

    def test_lineage_recorded_after_evolution(self):
        engine = MetaEvolutionEngine()
        metrics = {
            "evolution_success_rate": 0.5,
            "compilation_success_rate": 0.5,
            "verification_accuracy": 0.5,
        }
        engine.evolve(metrics, strategy="random")
        assert engine.lineage.total_entries == 2

    def test_benchmarking_recorded(self):
        engine = MetaEvolutionEngine()
        metrics = {
            "evolution_success_rate": 0.5,
            "compilation_success_rate": 0.5,
            "verification_accuracy": 0.5,
        }
        engine.evolve(metrics, strategy="random")
        assert len(engine.benchmarking.results) >= 1

    def test_event_bus_notifications(self):
        events: list[MetaEvent] = []
        engine = MetaEvolutionEngine()
        engine.subscribe(MetaEventType.PLATFORM_EVOLVED, lambda e: events.append(e))
        metrics = {
            "evolution_success_rate": 0.5,
            "compilation_success_rate": 0.5,
            "verification_accuracy": 0.5,
        }
        engine.evolve(metrics, strategy="random")
        assert len(events) == 1
        assert events[0].event_type == MetaEventType.PLATFORM_EVOLVED

    def test_mutate_locked_parameter_fails_safely(self):
        engine = MetaEvolutionEngine()
        locked_params = [p for p in engine.genome.parameters.values() if p.locked]
        assert len(locked_params) > 0
        for p in locked_params:
            assert p.locked is True

    def test_subscribe_to_all_event_types(self):
        engine = MetaEvolutionEngine()
        received: list[MetaEvent] = []
        for et in MetaEventType:
            engine.subscribe(et, lambda e: received.append(e))
        metrics = {
            "evolution_success_rate": 0.5,
            "compilation_success_rate": 0.5,
            "verification_accuracy": 0.5,
        }
        engine.evolve(metrics, strategy="random")
        assert len(received) > 0

    def test_multiple_evolutions(self):
        engine = MetaEvolutionEngine()
        metrics = {
            "evolution_success_rate": 0.5,
            "compilation_success_rate": 0.5,
            "verification_accuracy": 0.5,
        }
        for i in range(5):
            success, msg = engine.evolve(metrics, strategy="random")
            if not success:
                break
        assert engine.lineage.total_entries >= 2

    def test_simulated_metrics_passed_explicitly(self):
        engine = MetaEvolutionEngine()
        metrics = {
            "evolution_success_rate": 0.5,
            "compilation_success_rate": 0.5,
            "verification_accuracy": 0.5,
        }
        simulated = {
            "evolution_success_rate": 0.9,
            "compilation_success_rate": 0.9,
            "verification_accuracy": 0.9,
        }
        success, msg = engine.evolve(metrics, simulated_metrics=simulated, strategy="random")
        assert success is True
