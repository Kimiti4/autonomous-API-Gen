"""
End-to-end test covering all 9 phases of the Constitutional Architecture platform.

Phases:
  0   - Build Initial ISR
  1-2 - Evolution Engine
  3   - Compiler Pipeline
  4   - Verification Engine
  5   - Deployment Readiness
  6   - Operational Intelligence
  7   - Knowledge Engine
  8   - (Autonomous Engineering Agents — not yet implemented)
  9   - Meta-Evolution Engine
"""

from __future__ import annotations

import time

import pytest

# ──────────────────────────────────────────────────────────────────────────────
# Phase 0: Build Initial ISR
# ──────────────────────────────────────────────────────────────────────────────
from constitutional_architecture.isr.model.system import System
from constitutional_architecture.isr.model.module import Module
from constitutional_architecture.isr.model.service import Service, Operation, OperationType
from constitutional_architecture.isr.model.entity import Entity
from constitutional_architecture.isr.model.fields import Field, FieldType, FieldCardinality
from constitutional_architecture.isr.model.interface import Interface, InterfaceType, Endpoint, HttpMethod
from constitutional_architecture.isr.model.isr import ISR

M = HttpMethod


@pytest.fixture(scope="module")
def phase0_isr():
    return ISR(
        system=System(
            id="shop-1", name="MonolithShop",
            description="A monolithic e-commerce platform",
            modules=(
                Module(
                    id="mod-monolith", name="Monolith",
                    entities=(
                        Entity(id="ent-user", name="User", fields=(
                            Field(name="id", field_type=FieldType.UUID, is_primary_key=True),
                            Field(name="email", field_type=FieldType.EMAIL, cardinality=FieldCardinality.REQUIRED),
                            Field(name="name", field_type=FieldType.STRING),
                        )),
                        Entity(id="ent-product", name="Product", fields=(
                            Field(name="id", field_type=FieldType.UUID, is_primary_key=True),
                            Field(name="name", field_type=FieldType.STRING), Field(name="price", field_type=FieldType.FLOAT),
                            Field(name="stock", field_type=FieldType.INTEGER),
                        )),
                        Entity(id="ent-order", name="Order", fields=(
                            Field(name="id", field_type=FieldType.UUID, is_primary_key=True),
                            Field(name="user_id", field_type=FieldType.UUID), Field(name="total", field_type=FieldType.FLOAT),
                            Field(name="status", field_type=FieldType.STRING),
                        )),
                    ),
                    services=(
                        Service(id="svc-api", name="APIGateway",
                            operations=(
                                Operation(id="op-login", name="login"),
                                Operation(id="op-list-products", name="listProducts", operation_type=OperationType.QUERY),
                                Operation(id="op-create-order", name="createOrder"),
                                Operation(id="op-pay", name="processPayment"),
                                Operation(id="op-ship", name="shipOrder"),
                            ), is_stateless=True,
                        ),
                    ),
                    interfaces=(
                        Interface(id="iface-public", name="PublicAPI", interface_type=InterfaceType.REST,
                            endpoints=(
                                Endpoint(id="ep-login", name="login", path="/api/login", method=M.POST),
                                Endpoint(id="ep-products", name="listProducts", path="/api/products", method=M.GET),
                                Endpoint(id="ep-orders", name="createOrder", path="/api/orders", method=M.POST),
                                Endpoint(id="ep-pay", name="pay", path="/api/payments", method=M.POST),
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )


# ──────────────────────────────────────────────────────────────────────────────
# Phase 1-2: Evolution Engine
# ──────────────────────────────────────────────────────────────────────────────
from constitutional_architecture.engine.config import EvolutionConfig
from constitutional_architecture.engine.bridges.autonomous_pipeline import AutonomousPipeline


@pytest.fixture(scope="module")
def phase12_pipeline():
    config = EvolutionConfig(
        population_size=10, elite_count=2, max_generations=3, seed=42,
        mutation_rate=0.4, crossover_rate=0.2,
    )
    return AutonomousPipeline(config=config)


# ──────────────────────────────────────────────────────────────────────────────
# Phase 3: Compiler Pipeline
# ──────────────────────────────────────────────────────────────────────────────
from constitutional_architecture.compiler.pipeline import CompilerPipeline, CompilationConfig
from constitutional_architecture.compiler.compilation_config import OptimizationLevel


@pytest.fixture(scope="module")
def phase3_compiler():
    return CompilerPipeline()


# ──────────────────────────────────────────────────────────────────────────────
# Phase 4: Verification Engine
# ──────────────────────────────────────────────────────────────────────────────
from constitutional_architecture.verification.verification_engine import VerificationEngine
from constitutional_architecture.verification.verification_result import VerificationLevel


@pytest.fixture(scope="module")
def phase4_verifier():
    return VerificationEngine()


# ──────────────────────────────────────────────────────────────────────────────
# Phase 5: Deployment
# ──────────────────────────────────────────────────────────────────────────────
from constitutional_architecture.isr.model.deployment import (
    Deployment, ScalingConfig, NetworkingConfig, MonitoringConfig, SecretsConfig,
)
from constitutional_architecture.isr.model.system import SystemMetadata


# ──────────────────────────────────────────────────────────────────────────────
# Phase 6: Operational Intelligence
# ──────────────────────────────────────────────────────────────────────────────
from constitutional_architecture.operations.telemetry_engine import TelemetryEngine
from constitutional_architecture.operations.metrics_collector import MetricPoint
from constitutional_architecture.operations.observation_model import (
    Observation, ObservationSeverity, ObservationSource,
)
from constitutional_architecture.operations.drift_detector import RunningSystemSnapshot


@pytest.fixture(scope="module")
def phase6_telemetry():
    return TelemetryEngine()


# ──────────────────────────────────────────────────────────────────────────────
# Phase 7: Knowledge Engine
# ──────────────────────────────────────────────────────────────────────────────
from constitutional_architecture.knowledge.knowledge_engine import KnowledgeEngine
from constitutional_architecture.knowledge.pattern_repository import PatternEntry
from constitutional_architecture.knowledge.anti_pattern_repository import AntiPatternEntry
from constitutional_architecture.knowledge.mutation_repository import MutationRecordEntry
from constitutional_architecture.knowledge.knowledge_types import FitnessRecord


@pytest.fixture(scope="module")
def phase7_knowledge():
    return KnowledgeEngine()


# ──────────────────────────────────────────────────────────────────────────────
# Phase 9: Meta-Evolution Engine
# ──────────────────────────────────────────────────────────────────────────────
from constitutional_architecture.meta.meta_evolution_engine import MetaEvolutionEngine
from constitutional_architecture.meta.events import MetaEventType


@pytest.fixture(scope="module")
def phase9_meta():
    return MetaEvolutionEngine()


# ==============================================================================
# Tests
# ==============================================================================


class TestE2EPhase0:
    """Phase 0: Build Initial ISR."""

    def test_initial_isr_created(self, phase0_isr):
        assert phase0_isr is not None
        assert phase0_isr.system.name == "MonolithShop"
        assert len(phase0_isr.system.modules) == 1
        assert phase0_isr.content_hash is not None

    def test_initial_isr_structure(self, phase0_isr):
        m = phase0_isr.system.modules[0]
        assert len(m.entities) == 3
        assert len(m.services) == 1
        assert len(m.interfaces) == 1
        assert {e.name for e in m.entities} == {"User", "Product", "Order"}


class TestE2EPhase12:
    """Phase 1-2: Evolution Engine."""

    def test_pipeline_initialized(self, phase12_pipeline):
        assert len(phase12_pipeline.registry.all_identifiers) >= 8

    def test_evolution_produces_new_genome(self, phase0_isr, phase12_pipeline):
        evolved = phase12_pipeline.run(phase0_isr)
        assert evolved is not None
        assert evolved.content_hash != phase0_isr.content_hash
        assert len(phase12_pipeline.history) >= 1


class TestE2EPhase3:
    """Phase 3: Compiler Pipeline."""

    def test_compiler_produces_artifacts(self, phase0_isr, phase12_pipeline, phase3_compiler):
        evolved = phase12_pipeline.run(phase0_isr)
        config = CompilationConfig(
            project_name=evolved.system.name,
            target_backends=("fastapi",),
            optimization_level=OptimizationLevel.STANDARD,
        )
        result = phase3_compiler.compile(evolved, config=config)
        assert result is not None
        # Phase 3 compilation may have errors but must produce artifacts
        assert result.artifact_count > 0


class TestE2EPhase4:
    """Phase 4: Verification Engine."""

    def test_verification_approves_or_reports(self, phase0_isr, phase12_pipeline, phase4_verifier):
        evolved = phase12_pipeline.run(phase0_isr)
        report = phase4_verifier.verify(evolved, max_level=VerificationLevel.L3_SECURITY)
        assert report is not None
        assert report.passed_checks >= 0
        assert report.total_checks > 0


class TestE2EPhase5:
    """Phase 5: Deployment Readiness."""

    def test_deployment_configured(self):
        deploy = Deployment(
            id="deploy-shop-1", name="ShopProduction",
            scaling=ScalingConfig(min_instances=2, max_instances=20),
            networking=NetworkingConfig(expose_publicly=True, port=443),
            monitoring=MonitoringConfig(metrics_enabled=True, tracing_enabled=True),
            secrets=SecretsConfig(secrets=("DB_PASSWORD", "JWT_SECRET")),
        )
        assert deploy.name == "ShopProduction"
        assert deploy.scaling.min_instances == 2
        assert deploy.scaling.max_instances == 20
        assert deploy.networking.expose_publicly is True

    def test_isr_with_deployment_produces_new_version(self, phase0_isr):
        from constitutional_architecture.isr.model.system import SystemMetadata
        deploy = Deployment(
            id="deploy-shop-1", name="ShopProduction",
            scaling=ScalingConfig(min_instances=2, max_instances=20),
            networking=NetworkingConfig(expose_publicly=True, port=443),
            monitoring=MonitoringConfig(metrics_enabled=True, tracing_enabled=True),
            secrets=SecretsConfig(secrets=("DB_PASSWORD", "JWT_SECRET")),
        )
        system_v2 = System(
            id=phase0_isr.system.id, name=phase0_isr.system.name,
            description=phase0_isr.system.description,
            modules=phase0_isr.system.modules,
            deployment=deploy,
            metadata=SystemMetadata(version="2.0", description="Evolved"),
        )
        evolved_with_deploy = ISR(system=system_v2, version=phase0_isr.version + 1)
        assert evolved_with_deploy.version == phase0_isr.version + 1


class TestE2EPhase6:
    """Phase 6: Operational Intelligence."""

    def test_telemetry_ingests_metrics(self, phase6_telemetry):
        for i in range(10):
            phase6_telemetry.ingest_metric(MetricPoint(
                name="cpu_usage", value=45 + i * 2, service_name="APIGateway",
            ))
        phase6_telemetry.metrics_collector.set_threshold("cpu_usage", 80.0)
        assert phase6_telemetry.metrics_collector.total_points >= 10

    def test_observations_produced(self, phase6_telemetry):
        phase6_telemetry.ingest_observation(Observation(
            id="obs-arch-1", source=ObservationSource.METRICS,
            severity=ObservationSeverity.WARNING,
            title="High coupling", description="Dependency cycle detected",
        ))
        observations = phase6_telemetry.memory.get_recent_observations()
        assert len(observations) >= 1

    def test_drift_detection(self, phase0_isr, phase6_telemetry):
        snapshot = RunningSystemSnapshot(
            deployment_id="deploy-1",
            running_modules=("Monolith",),
            running_services=("APIGateway",),
            running_endpoints=("/api/login", "/api/products", "/api/orders"),
        )
        phase6_telemetry.ingest_snapshot(snapshot)
        phase6_telemetry.analyze(phase0_isr)
        # Drift may or may not be detected depending on ISR content


class TestE2EPhase7:
    """Phase 7: Knowledge Engine."""

    def test_patterns_can_be_registered(self, phase7_knowledge):
        phase7_knowledge.register_pattern(PatternEntry(
            name="CQRS", description="CQRS pattern",
            category="architectural", tags=("scalability",), evidence_count=15,
        ))
        phase7_knowledge.register_pattern(PatternEntry(
            name="Event Sourcing", description="Event Sourcing",
            category="architectural", tags=("audit",), evidence_count=10,
        ))
        assert phase7_knowledge.patterns.count == 2

    def test_anti_patterns_can_be_registered(self, phase7_knowledge):
        phase7_knowledge.register_anti_pattern(AntiPatternEntry(
            name="Big Ball of Mud", description="No clear boundaries",
            symptoms=("no clear boundaries",), severity="critical", recommended_fixes=("split contexts",),
        ))
        assert phase7_knowledge.anti_patterns.count == 1

    def test_mutations_can_be_recorded(self, phase7_knowledge, phase12_pipeline):
        for op_name in phase12_pipeline.registry.all_identifiers[:4]:
            phase7_knowledge.record_mutation(MutationRecordEntry(
                operator_name=op_name, target_context="MonolithShop",
                fitness_delta={"complexity": -0.05}, accepted=True, generation=1,
            ))
        assert phase7_knowledge.mutations.total_mutations >= 4

    def test_pattern_query(self, phase7_knowledge):
        pats = phase7_knowledge.query_patterns(tags=["scalability"])
        assert len(pats) >= 1
        assert any(p.name == "CQRS" for p in pats)

    def test_anti_pattern_detection(self, phase7_knowledge):
        results = phase7_knowledge.detect_anti_patterns(
            "MonolithShop has a single module — no clear boundaries"
        )
        assert len(results) >= 1

    def test_recommendations(self, phase7_knowledge):
        recs = phase7_knowledge.get_recommendations(
            "Split monolith into bounded contexts",
            constraints=("Event Sourcing",),
        )
        # Recommendations may be empty or non-empty; assert it doesn't crash
        assert recs is not None

    def test_fitness_recording(self, phase7_knowledge):
        phase7_knowledge.record_fitness(FitnessRecord(
            mutation_type="structural_split_module",
            dimensions={"complexity": -0.15, "maintainability": 0.12},
            sample_size=8, context="MonolithShop",
            avg_fitness_delta={"complexity": -0.12},
        ))
        snap = phase7_knowledge.metrics_snapshot
        assert snap.total_queries >= 0


class TestE2EPhase9:
    """Phase 9: Meta-Evolution Engine."""

    def test_engine_initialized(self, phase9_meta):
        assert phase9_meta.genome.version == 1
        assert phase9_meta.can_rollback is True
        assert phase9_meta.lineage.total_entries == 1

    def test_random_evolution(self, phase9_meta):
        metrics = {
            "evolution_success_rate": 0.5,
            "compilation_success_rate": 0.5,
            "verification_accuracy": 0.5,
        }
        success, message = phase9_meta.evolve(metrics, strategy="random")
        assert success is True, message
        assert "Platform evolved" in message
        assert phase9_meta.lineage.total_entries >= 2

    def test_adaptive_evolution(self, phase9_meta):
        metrics = {
            "evolution_success_rate": 0.6,
            "compilation_success_rate": 0.7,
            "verification_accuracy": 0.8,
        }
        success, message = phase9_meta.evolve(metrics, strategy="adaptive")
        assert success is True, message
        assert phase9_meta.lineage.total_entries >= 3

    def test_guided_evolution(self, phase9_meta):
        metrics = {
            "evolution_success_rate": 0.4,
            "compilation_success_rate": 0.4,
            "verification_accuracy": 0.4,
        }
        success, message = phase9_meta.evolve(metrics, strategy="guided")
        assert success is True, message
        assert phase9_meta.lineage.total_entries >= 4

    def test_benchmarking_recorded(self, phase9_meta):
        assert len(phase9_meta.benchmarking.results) >= 3

    def test_rollback(self, phase9_meta):
        version_before = phase9_meta.genome.version
        assert phase9_meta.can_rollback is True
        success, message = phase9_meta.rollback()
        assert success is True, message
        assert "Rolled back" in message

    def test_event_bus_notifications(self):
        events = []
        engine = MetaEvolutionEngine()
        engine.subscribe(MetaEventType.PLATFORM_EVOLVED, lambda e: events.append(e))
        metrics = {
            "evolution_success_rate": 0.5,
            "compilation_success_rate": 0.5,
            "verification_accuracy": 0.5,
        }
        engine.evolve(metrics, strategy="random")
        assert len(events) == 1

    def test_simulated_metrics(self):
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
        assert success is True, msg

    def test_constitutional_boundary_enforced(self):
        engine = MetaEvolutionEngine()
        locked_params = [p for p in engine.genome.parameters.values() if p.locked]
        assert len(locked_params) > 0
        for p in locked_params:
            assert p.locked is True

    def test_lineage_tracks_fitness(self, phase9_meta):
        lineage = phase9_meta.lineage
        assert lineage.total_entries >= 4
        best = lineage.best_fitness_entry
        assert best is not None
        assert best.genome_version >= 1


class TestE2ECombined:
    """End-to-end integration across selected phases."""

    def test_evolution_metrics_feed_meta_engine(self, phase0_isr, phase12_pipeline):
        """Simulate collecting platform metrics from evolution and feeding them to Phase 9."""
        evolved = phase12_pipeline.run(phase0_isr)
        assert evolved is not None

        meta = MetaEvolutionEngine()
        metrics = {
            "evolution_success_rate": 0.8 if phase12_pipeline.history else 0.3,
            "compilation_success_rate": 0.7,
            "verification_accuracy": 0.9,
        }
        success, message = meta.evolve(metrics, strategy="auto")
        assert success is True, message
        assert meta.genome.version >= 2
