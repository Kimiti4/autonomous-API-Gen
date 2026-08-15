import pytest

from constitutional_architecture.engine.bridges.autonomous_pipeline import AutonomousPipeline
from constitutional_architecture.engine.config import EvolutionConfig
from constitutional_architecture.isr.model.entity import Entity
from constitutional_architecture.isr.model.fields import Field, FieldCardinality, FieldType
from constitutional_architecture.isr.model.isr import ISR
from constitutional_architecture.isr.model.module import Module
from constitutional_architecture.isr.model.service import Operation, OperationType, Service
from constitutional_architecture.isr.model.system import System


def _seed_isr() -> ISR:
    return ISR(
        system=System(
            id="sys-test", name="TestShop",
            modules=(
                Module(
                    id="mod-core", name="Core",
                    entities=(
                        Entity(id="ent-user", name="User",
                               fields=(Field(name="id", field_type=FieldType.UUID, cardinality=FieldCardinality.REQUIRED),)),
                    ),
                    services=(
                        Service(id="svc-auth", name="AuthService",
                                operations=(Operation(id="op-login", name="login", operation_type=OperationType.COMMAND),)),
                    ),
                ),
            ),
        ),
    )


class TestAutonomousPipeline:
    def test_initialise(self):
        config = EvolutionConfig(population_size=10, elite_count=2, max_generations=2, seed=42)
        pipeline = AutonomousPipeline(config=config)
        assert pipeline.registry is not None
        assert pipeline.loop is not None

    def test_run_returns_isr(self):
        config = EvolutionConfig(population_size=10, elite_count=2, max_generations=2, seed=42)
        pipeline = AutonomousPipeline(config=config)
        result = pipeline.run(_seed_isr())
        assert isinstance(result, ISR)

    def test_history_recorded(self):
        config = EvolutionConfig(population_size=10, elite_count=2, max_generations=2, seed=42)
        pipeline = AutonomousPipeline(config=config)
        pipeline.run(_seed_isr())
        assert len(pipeline.history) == 1
        assert "evolved_hash" in pipeline.history[0]
        assert "verification_passed" in pipeline.history[0]

    def test_run_multiple_times(self):
        config = EvolutionConfig(population_size=10, elite_count=2, max_generations=2, seed=42)
        pipeline = AutonomousPipeline(config=config)
        pipeline.run(_seed_isr())
        pipeline.run(_seed_isr())
        assert len(pipeline.history) == 2
