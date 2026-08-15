import hashlib

import pytest

from constitutional_architecture.core.learning.engine import RuntimeLearningEngine
from constitutional_architecture.core.learning.fitness_update import (
    FitnessUpdateAlgorithm, GENE_LADDERS, step_gene,
)
from constitutional_architecture.core.learning.models import (
    EndpointObservation, MutationDirective, RuntimeObservation,
)
from constitutional_architecture.core.models.genome import (
    APIDesign, ApplicationArchitecture, ArchitectureGenome,
    DeploymentTopology, ObservabilityStrategy, ResiliencePosture,
    StateManagement,
)
from constitutional_architecture.core.models.intent import (
    BusinessArchetype, Capability, IntentModel, Persona, QualityAttribute,
)
from constitutional_architecture.core.models.isr import (
    EdgeType, ISREdge, ISRNode, NodeType, UniversalISR,
)
from constitutional_architecture.core.pipeline.isr_transpiler import ISRTranspiler


def make_genome(genome_id="gen42", intent_hash="abc123") -> ArchitectureGenome:
    return ArchitectureGenome(genome_id=genome_id, intent_hash=intent_hash)


def make_isr_with_slos(reliability=0.99, tolerance_ms=200.0) -> UniversalISR:
    isr = UniversalISR(intent_hash="abc123", genome_hash="def456")
    isr.add_node(ISRNode(id="api_orders", type=NodeType.API_ENDPOINT,
                         semantic_attributes={"path": "/v1/orders"}))
    isr.add_node(ISRNode(id="slo_api_orders", type=NodeType.SLO_DEFINITION,
                         semantic_attributes={
                             "reliability_target": reliability,
                             "error_budget": round(1.0 - reliability, 4),
                             "latency_tolerance_ms": tolerance_ms,
                         }))
    isr.add_edge(ISREdge(source_id="api_orders", target_id="slo_api_orders",
                         type=EdgeType.MONITORS))
    return isr


def healthy_observation(genome_id="gen42", endpoint_id="api_orders",
                        p95=50.0, error_rate=0.0005,
                        availability=0.995) -> RuntimeObservation:
    return RuntimeObservation(
        genome_id=genome_id,
        endpoints=(EndpointObservation(
            endpoint_id=endpoint_id, request_rate=100.0,
            error_rate=error_rate, p95_latency_ms=p95,
            availability=availability,
        ),),
    )


class TestSLOAttainment:
    def test_met_slo(self):
        algorithm = FitnessUpdateAlgorithm()
        attr = algorithm.compute_attainment(
            {"reliability_target": 0.99, "error_budget": 0.01,
             "latency_tolerance_ms": 200.0},
            EndpointObservation(endpoint_id="e", availability=0.995,
                                p95_latency_ms=50.0, error_rate=0.0005),
        )
        assert attr.observed
        assert attr.met
        assert attr.availability_attainment == 1.0
        assert attr.budget_burn == pytest.approx(0.05)

    def test_latency_breach_attainment_ratio(self):
        algorithm = FitnessUpdateAlgorithm()
        attr = algorithm.compute_attainment(
            {"reliability_target": 0.99, "error_budget": 0.01,
             "latency_tolerance_ms": 200.0},
            EndpointObservation(endpoint_id="e", availability=0.999,
                                p95_latency_ms=400.0),
        )
        assert not attr.met
        assert attr.latency_attainment == pytest.approx(0.5)
        assert attr.availability_attainment == 1.0

    def test_availability_breach(self):
        algorithm = FitnessUpdateAlgorithm()
        attr = algorithm.compute_attainment(
            {"reliability_target": 0.99, "error_budget": 0.01,
             "latency_tolerance_ms": 200.0},
            EndpointObservation(endpoint_id="e", availability=0.97,
                                p95_latency_ms=50.0, error_rate=0.03),
        )
        assert not attr.met
        assert attr.budget_burn == pytest.approx(3.0)

    def test_unobserved_slo_is_not_met(self):
        algorithm = FitnessUpdateAlgorithm()
        attr = algorithm.compute_attainment(
            {"reliability_target": 0.99, "error_budget": 0.01,
             "latency_tolerance_ms": 200.0},
            None,
        )
        assert not attr.observed
        assert not attr.met


class TestFitnessMultiplier:
    def test_healthy_system_boosts_multiplier(self):
        genome = make_genome()
        isr = make_isr_with_slos()
        update = FitnessUpdateAlgorithm().evaluate(
            genome, isr, [healthy_observation().endpoints[0]])
        assert update.runtime_multiplier == pytest.approx(1.1)
        assert update.final_fitness > update.static_fitness

    def test_breached_system_drags_multiplier(self):
        genome = make_genome()
        isr = make_isr_with_slos(reliability=0.99)
        update = FitnessUpdateAlgorithm().evaluate(
            genome, isr,
            [EndpointObservation(endpoint_id="api_orders", availability=0.90,
                                 p95_latency_ms=1000.0, error_rate=0.05)],
        )
        assert update.runtime_multiplier < 0.7
        assert update.final_fitness < update.static_fitness

    def test_no_slos_keeps_multiplier_neutral(self):
        genome = make_genome()
        isr = UniversalISR(intent_hash="abc123", genome_hash="def456")
        isr.add_node(ISRNode(id="api_orders", type=NodeType.API_ENDPOINT))
        update = FitnessUpdateAlgorithm().evaluate(
            genome, isr, [healthy_observation().endpoints[0]])
        assert update.runtime_multiplier == 1.0

    def test_missing_telemetry_drags_multiplier(self):
        genome = make_genome()
        isr = make_isr_with_slos()
        update = FitnessUpdateAlgorithm().evaluate(genome, isr, [])
        assert update.runtime_multiplier == pytest.approx(0.5)
        assert update.final_fitness < update.static_fitness

    def test_uniform_multiplier_min(self):
        genome = make_genome()
        isr = make_isr_with_slos(reliability=0.99)
        update = FitnessUpdateAlgorithm().evaluate(
            genome, isr,
            [EndpointObservation(endpoint_id="api_orders", availability=0.0,
                                 p95_latency_ms=5000.0, error_rate=0.5)],
        )
        assert update.runtime_multiplier == pytest.approx(0.5)


class TestDirectives:
    def test_availability_breach_directives(self):
        genome = make_genome()
        isr = make_isr_with_slos()
        update = FitnessUpdateAlgorithm().evaluate(
            genome, isr,
            [EndpointObservation(endpoint_id="api_orders", availability=0.95,
                                 p95_latency_ms=50.0, error_rate=0.03)],
        )
        genes = {d.gene_id: d for d in update.directives}
        assert genes["fault_tolerance"].action == "increase"
        assert genes["resilience_posture"].action == "increase"
        assert genes["deployment_topology"].action == "increase"
        assert "availability" in genes["fault_tolerance"].rationale

    def test_latency_breach_directives(self):
        genome = make_genome()
        isr = make_isr_with_slos(tolerance_ms=200.0)
        update = FitnessUpdateAlgorithm().evaluate(
            genome, isr,
            [EndpointObservation(endpoint_id="api_orders", availability=0.999,
                                 p95_latency_ms=450.0)],
        )
        genes = {d.gene_id: d for d in update.directives}
        assert genes["api_design"].action == "increase"
        assert genes["state_management"].action == "increase"

    def test_missing_telemetry_directives(self):
        genome = make_genome()
        isr = make_isr_with_slos()
        update = FitnessUpdateAlgorithm().evaluate(genome, isr, [])
        genes = {d.gene_id: d for d in update.directives}
        assert genes["observability_strategy"].action == "increase"
        assert genes["observability_depth"].action == "increase"

    def test_healthy_system_throttles_cost(self):
        genome = make_genome()
        isr = make_isr_with_slos()
        update = FitnessUpdateAlgorithm().evaluate(
            genome, isr, [healthy_observation().endpoints[0]])
        genes = {d.gene_id: d for d in update.directives}
        assert genes["cost_monitoring_intensity"].action == "decrease"
        assert genes["deployment_topology"].action == "decrease"

    def test_deduplication_keeps_highest_severity(self):
        algorithm = FitnessUpdateAlgorithm()
        directives = [
            MutationDirective("observability_depth", "increase", 0.3, "a"),
            MutationDirective("observability_depth", "increase", 0.9, "b"),
        ]
        genome = make_genome()
        candidate, applied = algorithm.apply_directives(genome, directives)
        assert len(applied) == 1
        assert applied[0].rationale == "b"


class TestStepGene:
    def test_categorical_ladder_steps(self):
        genome = make_genome()
        assert step_gene(genome, "resilience_posture", "increase") == \
            ResiliencePosture.BULKHEAD_ISOLATION
        assert step_gene(genome, "api_design", "increase") == APIDesign.EVENT_STREAM
        assert step_gene(genome, "deployment_topology", "increase") == \
            DeploymentTopology.ON_PREM

    def test_ladder_extreme_is_noop(self):
        genome = make_genome()
        genome.set_gene("resilience_posture", ResiliencePosture.BULKHEAD_ISOLATION)
        assert step_gene(genome, "resilience_posture", "increase") is None
        assert step_gene(genome, "resilience_posture", "decrease") == \
            ResiliencePosture.CIRCUIT_BREAKER

    def test_continuous_step_within_bounds(self):
        genome = make_genome()
        old = genome.get_gene("fault_tolerance")
        new = step_gene(genome, "fault_tolerance", "increase")
        assert new > old
        gene = genome.continuous_genes["fault_tolerance"]
        assert gene.min_value <= new <= gene.max_value

    def test_continuous_extreme_noop(self):
        genome = make_genome()
        genome.continuous_genes["fault_tolerance"].value = \
            genome.continuous_genes["fault_tolerance"].max_value
        assert step_gene(genome, "fault_tolerance", "increase") is None

    def test_unknown_gene_noop(self):
        assert step_gene(make_genome(), "nonexistent_gene", "increase") is None

    def test_ladders_cover_directive_genes(self):
        assert "resilience_posture" in GENE_LADDERS
        assert "deployment_topology" in GENE_LADDERS
        assert "api_design" in GENE_LADDERS
        assert "state_management" in GENE_LADDERS
        assert "observability_strategy" in GENE_LADDERS


class TestApplyDirectives:
    def test_candidate_mutates_genes_only(self):
        genome = make_genome()
        isr = make_isr_with_slos()
        update = FitnessUpdateAlgorithm().evaluate(
            genome, isr,
            [EndpointObservation(endpoint_id="api_orders", availability=0.94,
                                 p95_latency_ms=50.0, error_rate=0.04)],
        )
        candidate, applied = FitnessUpdateAlgorithm().apply_directives(
            genome, update.directives)
        assert candidate is not genome
        assert candidate.genome_id == genome.genome_id
        assert candidate.get_gene("fault_tolerance") > genome.get_gene("fault_tolerance")
        assert candidate.get_gene("resilience_posture") == \
            ResiliencePosture.BULKHEAD_ISOLATION
        assert applied

    def test_noop_at_extreme_leaves_gene_unchanged(self):
        genome = make_genome()
        genome.set_gene("resilience_posture", ResiliencePosture.BULKHEAD_ISOLATION)
        candidate, applied = FitnessUpdateAlgorithm().apply_directives(
            genome, [MutationDirective("resilience_posture", "increase", 0.9, "x")])
        assert candidate.get_gene("resilience_posture") == \
            ResiliencePosture.BULKHEAD_ISOLATION
        assert applied == []

    def test_max_severity_gate(self):
        genome = make_genome()
        candidate, applied = FitnessUpdateAlgorithm().apply_directives(
            genome,
            [MutationDirective("fault_tolerance", "increase", 0.9, "high"),
             MutationDirective("api_design", "increase", 0.2, "low")],
            max_severity=0.5,
        )
        assert candidate.get_gene("api_design") == APIDesign.EVENT_STREAM
        assert candidate.get_gene("fault_tolerance") == genome.get_gene("fault_tolerance")
        assert len(applied) == 1

    def test_clone_isolation(self):
        genome = make_genome()
        candidate, _ = FitnessUpdateAlgorithm().apply_directives(
            genome, [MutationDirective("fault_tolerance", "increase", 0.5, "x")])
        assert genome.get_gene("fault_tolerance") != candidate.get_gene("fault_tolerance")


class TestRuntimeLearningEngine:
    def test_ingest_rejects_misattributed_telemetry(self):
        engine = RuntimeLearningEngine(make_genome(), make_isr_with_slos())
        with pytest.raises(ValueError, match="provenance"):
            engine.ingest(healthy_observation(genome_id="other_genome"))

    def test_ingest_records_iteration(self):
        engine = RuntimeLearningEngine(make_genome(), make_isr_with_slos())
        update = engine.ingest(healthy_observation())
        assert len(engine.iterations) == 1
        assert engine.iterations[0].number == 1
        assert engine.iterations[0].final_fitness == update.final_fitness
        assert engine.iterations[0].previous_fitness == update.static_fitness
        assert engine.latest_update is update

    def test_learning_trend_across_windows(self):
        engine = RuntimeLearningEngine(make_genome(), make_isr_with_slos())
        engine.ingest(healthy_observation())
        first = engine.fitness_history()[0]
        engine.ingest(healthy_observation())
        assert engine.fitness_history() == (first, first)
        assert engine.improvement == 0.0

    def test_candidate_from_latest_update(self):
        engine = RuntimeLearningEngine(make_genome(), make_isr_with_slos())
        engine.ingest(RuntimeObservation(
            genome_id="gen42",
            endpoints=(EndpointObservation(
                endpoint_id="api_orders", availability=0.95,
                p95_latency_ms=400.0, error_rate=0.02),),
        ))
        candidate, applied = engine.propose_candidate()
        assert candidate is not engine.genome
        assert candidate.genome_id == "gen42"
        assert applied
        assert len(engine.candidates) == 1

    def test_propose_without_ingest_raises(self):
        engine = RuntimeLearningEngine(make_genome(), make_isr_with_slos())
        with pytest.raises(ValueError, match="No learning iteration"):
            engine.propose_candidate()

    def test_phase6_signal_bridge(self):
        engine = RuntimeLearningEngine(make_genome(), make_isr_with_slos())
        update = engine.ingest_signals(
            {"reliability": 0.6, "performance": 0.9, "observability": 0.4},
            genome_id="gen42",
        )
        assert 0.5 <= update.runtime_multiplier <= 1.1
        genes = {d.gene_id for d in update.directives}
        assert "fault_tolerance" in genes
        assert "observability_strategy" in genes
        assert len(engine.iterations) == 1

    def test_quality_priorities_weight_static_fitness(self):
        genome = make_genome()
        priorities = {QualityAttribute.SECURITY: 1.0,
                      QualityAttribute.MAINTAINABILITY: 0.0,
                      QualityAttribute.COST_EFFICIENCY: 0.0,
                      QualityAttribute.PERFORMANCE: 0.0,
                      QualityAttribute.SCALABILITY: 0.0,
                      QualityAttribute.OBSERVABILITY: 0.0,
                      QualityAttribute.RELIABILITY: 0.0,
                      QualityAttribute.AI_READINESS: 0.0}
        engine = RuntimeLearningEngine(genome, make_isr_with_slos(),
                                       quality_priorities=priorities)
        update = engine.ingest(healthy_observation())
        security_only = engine.genome
        security_only.set_gene("security_arch", "zero_trust")
        assert update.static_fitness > 0.5


class TestEndToEndLoop:
    def test_closed_loop_over_transpiled_isr(self):
        intent = IntentModel(
            project_name="Nexus",
            problem_statement="High-scale data processing",
            personas=[Persona(name="Sys", role="admin",
                              primary_goals=["process"])],
            business_archetype=BusinessArchetype.DATA_PLATFORM,
            core_capabilities=[Capability(name="Ingest", description="d")],
            quality_priorities={
                QualityAttribute.RELIABILITY: 0.8,
                QualityAttribute.PERFORMANCE: 0.2,
            },
        )
        genome = make_genome()
        isr = ISRTranspiler().transpile(intent, genome)

        slo_nodes = [n for n in isr.nodes.values()
                     if n.type == NodeType.SLO_DEFINITION]
        assert slo_nodes

        engine = RuntimeLearningEngine(genome, isr,
                                       quality_priorities=intent.quality_priorities)
        endpoint_ids = [
            edge.source_id for edge in isr.edges
            if edge.type == EdgeType.MONITORS
        ]
        assert endpoint_ids
        engine.ingest(RuntimeObservation(
            genome_id="gen42",
            endpoints=tuple(
                EndpointObservation(endpoint_id=eid, availability=0.90,
                                    p95_latency_ms=900.0, error_rate=0.05)
                for eid in endpoint_ids
            ),
        ))
        candidate, applied = engine.propose_candidate()
        assert applied
        assert candidate.get_gene("fault_tolerance") > genome.get_gene("fault_tolerance")

        update2 = engine.ingest(healthy_observation())
        assert len(engine.iterations) == 2
        assert engine.fitness_history()[1] > 0.0
