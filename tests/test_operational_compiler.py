import copy
import json

import pytest

from constitutional_architecture.compilers.operational.intelligence.compiler import (
    OperationalIntelligenceCompiler,
)
from constitutional_architecture.core.models.bundle import ArtifactType
from constitutional_architecture.core.models.genome import ArchitectureGenome
from constitutional_architecture.core.models.intent import (
    BusinessArchetype, Capability, IntentModel, Persona, QualityAttribute,
)
from constitutional_architecture.core.models.isr import (
    EdgeType, ISREdge, ISRNode, NodeType, UniversalISR,
)
from constitutional_architecture.core.pipeline.isr_transpiler import ISRTranspiler


@pytest.fixture
def intent() -> IntentModel:
    return IntentModel(
        project_name="Nexus",
        problem_statement="High-scale data processing",
        personas=[Persona(name="Sys", role="admin", primary_goals=["process"])],
        business_archetype=BusinessArchetype.DATA_PLATFORM,
        core_capabilities=[Capability(name="Ingest", description="d")],
        quality_priorities={
            QualityAttribute.RELIABILITY: 0.95,
            QualityAttribute.PERFORMANCE: 0.9,
        },
    )


@pytest.fixture
def genome() -> ArchitectureGenome:
    g = ArchitectureGenome(genome_id="g1", intent_hash="1")
    g.set_gene("observability_depth", 0.9)
    return g


@pytest.fixture
def isr() -> UniversalISR:
    isr = UniversalISR(intent_hash="1", genome_hash="1")
    isr.add_node(ISRNode(
        id="api_orders",
        type=NodeType.API_ENDPOINT,
        semantic_attributes={"path": "/v1/orders"},
    ))
    isr.add_node(ISRNode(
        id="api_invoices",
        type=NodeType.API_ENDPOINT,
        semantic_attributes={"path": "/v1/invoices"},
    ))
    isr.add_node(ISRNode(
        id="slo_api_orders",
        type=NodeType.SLO_DEFINITION,
        semantic_attributes={
            "reliability_target": 0.99,
            "error_budget": 0.01,
            "latency_tolerance_ms": 250.0,
        },
    ))
    isr.add_node(ISRNode(
        id="slo_api_invoices",
        type=NodeType.SLO_DEFINITION,
        semantic_attributes={
            "reliability_target": 0.99,
            "error_budget": 0.01,
            "latency_tolerance_ms": 250.0,
        },
    ))
    isr.add_edge(ISREdge(source_id="api_orders", target_id="slo_api_orders", type=EdgeType.MONITORS))
    isr.add_edge(ISREdge(source_id="api_invoices", target_id="slo_api_invoices", type=EdgeType.MONITORS))
    isr.add_node(ISRNode(
        id="telemetry_core",
        type=NodeType.TELEMETRY_REQUIREMENT,
        semantic_attributes={"trace_sampling_percentage": 90.0, "latency_tolerance_ms": 250.0},
    ))
    isr.add_node(ISRNode(
        id="op_policy_circuit_breaker",
        type=NodeType.OPERATIONAL_POLICY,
        semantic_attributes={
            "resilience_posture": "circuit_breaker",
            "auditability_level": "standard",
            "cost_monitoring_intensity": 0.5,
            "observability_depth": 0.9,
        },
    ))
    return isr


def files_of(bundle):
    return bundle.manifests[0].files


class TestOperationalIntelligenceCompiler:
    def test_compiler_purity(self, intent, genome, isr):
        compiler = OperationalIntelligenceCompiler()
        snapshot = copy.deepcopy(isr)
        compiler.compile(isr, genome, {}, intent)
        assert isr == snapshot

    def test_compiles_full_operational_layer(self, intent, genome, isr):
        compiler = OperationalIntelligenceCompiler()
        files = files_of(compiler.compile(isr, genome, {}, intent))
        assert "slos/alert_rules.yaml" in files
        assert "telemetry/otel-collector.yaml" in files
        assert "dashboards/system_overview.json" in files
        assert "runbooks/incident_response.model.json" in files

    def test_alert_rules_derive_from_reliability_target(self, intent, genome, isr):
        compiler = OperationalIntelligenceCompiler()
        rules = files_of(compiler.compile(isr, genome, {}, intent))["slos/alert_rules.yaml"]
        assert 'slo_target: "0.99"' in rules
        assert "ErrorBudgetBurn" in rules
        assert "HighErrorRate" in rules

    def test_lower_reliability_raises_alert_threshold(self, intent, genome, isr):
        for node in isr.nodes.values():
            if node.type == NodeType.SLO_DEFINITION:
                node.semantic_attributes["reliability_target"] = 0.9
                node.semantic_attributes["error_budget"] = 0.1
        compiler = OperationalIntelligenceCompiler()
        rules = files_of(compiler.compile(isr, genome, {}, intent))["slos/alert_rules.yaml"]
        assert "> 0.2" in rules

    def test_endpoint_latency_alerts_from_slo_subgraph(self, intent, genome, isr):
        compiler = OperationalIntelligenceCompiler()
        rules = files_of(compiler.compile(isr, genome, {}, intent))["slos/alert_rules.yaml"]
        assert "HighLatency-v1_orders" in rules
        assert 'route="/v1/orders"' in rules
        assert "> 0.250" in rules

    def test_circuit_breaker_alert_only_when_posture_selected(self, intent, genome, isr):
        compiler = OperationalIntelligenceCompiler()
        rules = files_of(compiler.compile(isr, genome, {}, intent))["slos/alert_rules.yaml"]
        assert "CircuitBreakerOpen" in rules

        for node in isr.nodes.values():
            if node.type == NodeType.OPERATIONAL_POLICY:
                node.semantic_attributes["resilience_posture"] = "fail_fast"
        rules_ff = files_of(compiler.compile(isr, genome, {}, intent))["slos/alert_rules.yaml"]
        assert "CircuitBreakerOpen" not in rules_ff

    def test_strict_compliance_adds_audit_alert(self, intent, genome, isr):
        for node in isr.nodes.values():
            if node.type == NodeType.OPERATIONAL_POLICY:
                node.semantic_attributes["auditability_level"] = "strict_compliance"
        compiler = OperationalIntelligenceCompiler()
        rules = files_of(compiler.compile(isr, genome, {}, intent))["slos/alert_rules.yaml"]
        assert "AuditLogFailures" in rules

    def test_otel_sampling_from_projection(self, intent, genome, isr):
        compiler = OperationalIntelligenceCompiler()
        otel = files_of(compiler.compile(isr, genome, {}, intent))["telemetry/otel-collector.yaml"]
        assert "sampling_percentage: 90.0" in otel
        assert "probabilistic_sampler" in otel

    def test_sampling_falls_back_to_genome_gene(self, intent, genome, isr):
        for node in list(isr.nodes.values()):
            if node.type in (NodeType.TELEMETRY_REQUIREMENT, NodeType.OPERATIONAL_POLICY):
                isr.nodes.pop(node.id)
        genome.set_gene("observability_depth", 0.5)
        compiler = OperationalIntelligenceCompiler()
        otel = files_of(compiler.compile(isr, genome, {}, intent))["telemetry/otel-collector.yaml"]
        assert "sampling_percentage: 50.0" in otel

    def test_dashboard_maps_slo_nodes_to_panels(self, intent, genome, isr):
        compiler = OperationalIntelligenceCompiler()
        dashboard = json.loads(
            files_of(compiler.compile(isr, genome, {}, intent))["dashboards/system_overview.json"]
        )
        titles = [p["title"] for p in dashboard["panels"]]
        assert dashboard["slo_target"] == 0.99
        assert "Request Rate - /v1/orders" in titles
        assert "SLO Burn - /v1/orders" in titles
        assert "Request Rate - /v1/invoices" in titles

    def test_semantic_runbook_model(self, intent, genome, isr):
        compiler = OperationalIntelligenceCompiler()
        runbook = json.loads(
            files_of(compiler.compile(isr, genome, {}, intent))[
                "runbooks/incident_response.model.json"
            ]
        )
        assert runbook["title"] == "System Incident Response"
        assert runbook["reliability_target"] == 0.99
        assert runbook["resilience_posture"] == "circuit_breaker"
        actions = [s["action"] for s in runbook["steps"]]
        assert "verify_slo_breach" in actions
        assert "check_circuit_breaker_states" in actions

    def test_runbook_omits_breaker_step_when_not_selected(self, intent, genome, isr):
        for node in isr.nodes.values():
            if node.type == NodeType.OPERATIONAL_POLICY:
                node.semantic_attributes["resilience_posture"] = "bulkhead_isolation"
        compiler = OperationalIntelligenceCompiler()
        runbook = json.loads(
            files_of(compiler.compile(isr, genome, {}, intent))[
                "runbooks/incident_response.model.json"
            ]
        )
        actions = [s["action"] for s in runbook["steps"]]
        assert "check_circuit_breaker_states" not in actions

    def test_deterministic_output(self, intent, genome, isr):
        compiler = OperationalIntelligenceCompiler()
        bundle1 = compiler.compile(isr, genome, {}, intent)
        bundle2 = compiler.compile(isr, genome, {}, intent)
        assert files_of(bundle1) == files_of(bundle2)

    def test_returns_compilation_bundle(self, intent, genome, isr):
        compiler = OperationalIntelligenceCompiler()
        bundle = compiler.compile(isr, genome, {}, intent)
        assert bundle.compiler_id == "operational_intelligence_v1"
        assert bundle.target_technology == "prometheus_grafana_otel"
        assert bundle.manifests[0].artifact_type == ArtifactType.CONFIGURATION
        assert bundle.exposed_interfaces["slo_target"] == 0.99

    def test_transpiler_projects_operational_subgraph(self, intent, genome):
        transpiler = ISRTranspiler()
        isr = transpiler.transpile(intent, genome)
        slos = [n for n in isr.nodes.values() if n.type == NodeType.SLO_DEFINITION]
        telemetry = [n for n in isr.nodes.values() if n.type == NodeType.TELEMETRY_REQUIREMENT]
        policies = [n for n in isr.nodes.values() if n.type == NodeType.OPERATIONAL_POLICY]
        assert len(slos) > 0
        assert len(telemetry) == 1
        assert len(policies) == 1
        monitored = {
            e.source_id for e in isr.edges
            if e.type == EdgeType.MONITORS
        }
        assert all(
            n.id in monitored
            for n in isr.nodes.values() if n.type == NodeType.API_ENDPOINT
        )

    def test_transpiled_projection_feeds_compiler(self, intent, genome):
        transpiler = ISRTranspiler()
        isr = transpiler.transpile(intent, genome)
        compiler = OperationalIntelligenceCompiler()
        files = files_of(compiler.compile(isr, genome, {}, intent))
        assert "slos/alert_rules.yaml" in files
        assert "runbooks/incident_response.model.json" in files

    def test_registry_integration(self, intent, genome, isr):
        from constitutional_architecture.core.registry.compiler_registry import (
            CompilerMetadata, CompilerRegistry,
        )
        registry = CompilerRegistry()
        registry.register(OperationalIntelligenceCompiler, CompilerMetadata(
            compiler_id="operational_intelligence_v1",
            target_technology="prometheus_grafana_otel",
            supported_domains=["operational"],
            required_genes=["observability_depth"],
        ))
        resolved = registry.resolve_compilers(genome, isr)
        assert "operational_intelligence_v1" in resolved
        bundle = registry.get_compiler("operational_intelligence_v1").compile(isr, genome, {}, intent)
        assert bundle.compiler_id == "operational_intelligence_v1"
