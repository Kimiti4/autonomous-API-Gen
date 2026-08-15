"""Integration tests for the Evolution Engine."""

import pytest

from constitutional_architecture.engine.config import EvolutionConfig
from constitutional_architecture.engine.evolution_engine import EvolutionEngine
from constitutional_architecture.engine.evolution_events import EventType
from constitutional_architecture.engine.mutation_registry import MutationOperatorSpec, MutationRegistry
from constitutional_architecture.isr.eir.taxonomy import MutationCategory, MutationClass
from constitutional_architecture.isr.model.entity import Entity
from constitutional_architecture.isr.model.fields import Field, FieldType
from constitutional_architecture.isr.model.isr import ISR
from constitutional_architecture.isr.model.module import Module
from constitutional_architecture.isr.model.service import Service, Operation, OperationType
from constitutional_architecture.isr.model.system import System


def _create_seed_isr() -> ISR:
    return ISR(
        system=System(
            id="test-system",
            name="TestShop",
            modules=(
                Module(
                    id="mod-auth",
                    name="Authentication",
                    entities=(
                        Entity(
                            id="ent-user",
                            name="User",
                            fields=(
                                Field(name="id", field_type=FieldType.UUID, is_primary_key=True),
                                Field(name="email", field_type=FieldType.EMAIL),
                            ),
                        ),
                    ),
                    services=(
                        Service(
                            id="svc-auth",
                            name="AuthService",
                            operations=(
                                Operation(id="op-login", name="login", operation_type=OperationType.COMMAND),
                            ),
                        ),
                    ),
                ),
                Module(
                    id="mod-orders",
                    name="Orders",
                    entities=(
                        Entity(
                            id="ent-order",
                            name="Order",
                            fields=(
                                Field(name="id", field_type=FieldType.UUID, is_primary_key=True),
                                Field(name="total", field_type=FieldType.DECIMAL),
                            ),
                        ),
                    ),
                    services=(
                        Service(
                            id="svc-orders",
                            name="OrderService",
                            operations=(
                                Operation(id="op-create", name="create_order", operation_type=OperationType.COMMAND),
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )


class TestEvolutionEngine:
    def test_initialise(self):
        config = EvolutionConfig(population_size=10, max_generations=5, seed=42)
        engine = EvolutionEngine(config=config)
        engine.initialise(_create_seed_isr())
        assert len(engine.get_population()) == 10

    def test_single_step(self):
        config = EvolutionConfig(population_size=10, max_generations=5, seed=42)
        engine = EvolutionEngine(config=config)
        engine.initialise(_create_seed_isr())
        result = engine.step()
        assert result.generation == 0
        assert result.population_size == 10
        assert result.best_fitness >= 0.0

    def test_run_multiple_generations(self):
        config = EvolutionConfig(population_size=10, max_generations=5, seed=42)
        engine = EvolutionEngine(config=config)
        engine.initialise(_create_seed_isr())
        result = engine.run(generations=3)
        assert result.generations_completed == 3
        assert result.best_individual is not None

    def test_reproducibility(self):
        config = EvolutionConfig(population_size=10, max_generations=3, seed=123)
        isr = _create_seed_isr()

        engine1 = EvolutionEngine(config=config)
        engine1.initialise(isr)
        result1 = engine1.run(generations=3)

        engine2 = EvolutionEngine(config=config)
        engine2.initialise(isr)
        result2 = engine2.run(generations=3)

        assert result1.best_individual is not None
        assert result2.best_individual is not None
        assert result1.best_individual.composite_fitness == result2.best_individual.composite_fitness

    def test_immutability_preserved(self):
        config = EvolutionConfig(population_size=5, max_generations=2, seed=42, elite_count=2)
        original_isr = _create_seed_isr()
        original_hash = original_isr.content_hash

        engine = EvolutionEngine(config=config)
        engine.initialise(original_isr)
        engine.run(generations=2)

        assert original_isr.content_hash == original_hash

    def test_events_published(self):
        config = EvolutionConfig(population_size=5, max_generations=2, seed=42, elite_count=2)
        engine = EvolutionEngine(config=config)

        events_received: list = []
        engine.subscribe(EventType.POPULATION_CREATED, lambda e: events_received.append(e))
        engine.subscribe(EventType.GENERATION_COMPLETED, lambda e: events_received.append(e))

        engine.initialise(_create_seed_isr())
        engine.run(generations=2)

        event_types = [e.event_type for e in events_received]
        assert EventType.POPULATION_CREATED in event_types
        assert EventType.GENERATION_COMPLETED in event_types

    def test_no_framework_knowledge(self):
        import constitutional_architecture.engine.evolution_engine as mod
        import inspect
        source = inspect.getsource(mod)
        forbidden = ["fastapi", "spring", "phoenix", "django", "nest", "react", "vue", "angular"]
        for term in forbidden:
            assert term not in source.lower(), f"Framework reference '{term}' found in engine"
