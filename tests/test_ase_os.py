"""
ASE-OS Integration Test: The Closed-Loop Evolutionary Cycle.

Proves that the ASE-OS kernels interact correctly, maintaining
constitutional boundaries while executing a full evolutionary learning
loop: multi-agent debate -> governance gate -> simulation -> runtime
experimentation -> empirical learning -> UEM lineage.
"""

import pytest

from constitutional_architecture.core.kernels.engineering.uem import (
    EventType, UEMEvent, UniversalEngineeringMemory,
)
from constitutional_architecture.core.kernels.evolution.simulator import (
    ArchitectureSimulator,
)
from constitutional_architecture.core.kernels.governance.agents import (
    Agent, AgentDirective, GovernanceKernel, GovernanceViolation,
)
from constitutional_architecture.core.kernels.learning.ckb import (
    EmpiricalEvidence, LearningKernel,
)
from constitutional_architecture.core.kernels.runtime.experimentation import (
    Experiment, ExperimentManager,
)
from constitutional_architecture.core.models.isr import (
    EdgeType, ISREdge, ISRNode, NodeType, UniversalISR,
)


class SecurityAgent(Agent):
    def reason(self, target_id: str) -> list:
        return [AgentDirective(
            agent_role=self.role, target_node="GLOBAL",
            attribute="encryption_at_rest", value=True,
            rationale="Constitutional mandate for sensitive data.",
        )]


class RogueAgent(Agent):
    def reason(self, target_id: str) -> list:
        return [AgentDirective(
            agent_role=self.role, target_node="GLOBAL",
            attribute="database", value="PostgreSQL",  # VIOLATION
            rationale="It's the best database.",
        )]


@pytest.fixture
def ase_os():
    uem = UniversalEngineeringMemory()
    gov = GovernanceKernel()
    sim = ArchitectureSimulator()
    runtime = ExperimentManager(uem)
    learning = LearningKernel(uem)
    return uem, gov, sim, runtime, learning


class TestGovernanceKernel:
    def test_governance_proof_is_deterministic(self):
        gov = GovernanceKernel()
        directive = AgentDirective(
            agent_role="Security", target_node="GLOBAL",
            attribute="encryption_at_rest", value=True,
            rationale="Constitutional mandate.",
        )
        assert gov.validate_directive(directive).startswith("gov_proof_")
        assert gov.validate_directive(directive) == \
            gov.validate_directive(directive)

    def test_rogue_technology_injection_blocked(self):
        gov = GovernanceKernel()
        rogue = AgentDirective(
            agent_role="Rogue", target_node="GLOBAL",
            attribute="database", value="PostgreSQL",
            rationale="It's the best database.",
        )
        with pytest.raises(GovernanceViolation, match="forbidden technology"):
            gov.validate_directive(rogue)


class TestArchitectureSimulator:
    def test_sync_hops_predict_latency(self):
        isr = UniversalISR(intent_hash="1", genome_hash="1")
        isr.add_node(ISRNode(id="svc_a", type=NodeType.SERVICE))
        isr.add_node(ISRNode(id="svc_b", type=NodeType.SERVICE))
        isr.add_edge(ISREdge(source_id="svc_a", target_id="svc_b",
                             type=EdgeType.DEPENDS_ON,
                             attributes={"sync": True}))

        sim = ArchitectureSimulator()
        assert sim.predict_latency(isr, {}) == 5.0

    def test_async_edges_add_no_latency(self):
        isr = UniversalISR(intent_hash="1", genome_hash="1")
        isr.add_node(ISRNode(id="svc_a", type=NodeType.SERVICE))
        isr.add_node(ISRNode(id="svc_b", type=NodeType.SERVICE))
        isr.add_edge(ISREdge(source_id="svc_a", target_id="svc_b",
                             type=EdgeType.DEPENDS_ON,
                             attributes={"sync": False}))

        sim = ArchitectureSimulator()
        assert sim.predict_latency(isr, {}) == 0.0

    def test_cost_scales_with_node_count(self):
        isr = UniversalISR(intent_hash="1", genome_hash="1")
        for i in range(4):
            isr.add_node(ISRNode(id=f"svc_{i}", type=NodeType.SERVICE))
        sim = ArchitectureSimulator()
        assert sim.predict_cost(isr, None) == 4 * 15.0


class TestExperimentManager:
    def test_telemetry_routed_by_watermark(self):
        uem = UniversalEngineeringMemory()
        runtime = ExperimentManager(uem)
        experiment = Experiment(
            experiment_id="exp_001",
            champion_genome_id="genome_mono",
            challenger_genome_id="genome_micro",
            traffic_split=0.2,
        )
        runtime.start_experiment(experiment)
        runtime.ingest_watermarked_telemetry("genome_mono", "p99_latency", 120.0)
        runtime.ingest_watermarked_telemetry("genome_micro", "p99_latency", 45.0)

        assert experiment.telemetry_champion["p99_latency"] == 120.0
        assert experiment.telemetry_challenger["p99_latency"] == 45.0
        assert runtime.conclude_experiment("exp_001") == "genome_micro"

    def test_unwatermarked_telemetry_not_routed(self):
        uem = UniversalEngineeringMemory()
        runtime = ExperimentManager(uem)
        runtime.start_experiment(Experiment(
            experiment_id="exp_002", champion_genome_id="a",
            challenger_genome_id="b", traffic_split=0.1))
        runtime.ingest_watermarked_telemetry("unrelated", "p99_latency", 1.0)
        assert runtime.conclude_experiment("exp_002") is None


class TestLearningKernel:
    def test_bayesian_confidence_update(self):
        uem = UniversalEngineeringMemory()
        learning = LearningKernel(uem)
        evidence = EmpiricalEvidence(
            experiment_id="exp_001", context="High-scale B2B",
            latency_ms=45.0, error_rate=0.01, outcome="survived")
        learning.record_outcome("Microservices_Pattern", evidence)

        assert learning.ckb["Microservices_Pattern"].confidence_score == 1.0

        learning.record_outcome("Microservices_Pattern", EmpiricalEvidence(
            experiment_id="exp_002", context="B2C",
            latency_ms=900.0, error_rate=0.2, outcome="deprecated"))
        assert learning.ckb["Microservices_Pattern"].confidence_score == 0.5


class TestFullASEOsLoop:
    def test_full_ase_os_loop(self, ase_os):
        uem, gov, sim, runtime, learning = ase_os

        # 1. Multi-Agent Debate (Phase 19)
        sec_agent = SecurityAgent("Security", uem, gov)
        rogue_agent = RogueAgent("Rogue", uem, gov)

        directives = sec_agent.reason("intent_1")
        sec_agent.act("intent_1", directives)

        with pytest.raises(GovernanceViolation, match="forbidden technology"):
            rogue_agent.act("intent_1", rogue_agent.reason("intent_1"))

        # 2. Architecture Simulation (Phase 18)
        isr = UniversalISR(intent_hash="1", genome_hash="1")
        isr.add_node(ISRNode(id="svc_a", type=NodeType.SERVICE))
        isr.add_node(ISRNode(id="svc_b", type=NodeType.SERVICE))
        isr.add_edge(ISREdge(source_id="svc_a", target_id="svc_b",
                             type=EdgeType.DEPENDS_ON,
                             attributes={"sync": True}))

        assert sim.predict_latency(isr, {}) == 5.0

        # 3. Runtime Experimentation (Phase 16)
        experiment = Experiment(
            experiment_id="exp_001",
            champion_genome_id="genome_mono",
            challenger_genome_id="genome_micro",
            traffic_split=0.2,
        )
        runtime.start_experiment(experiment)
        runtime.ingest_watermarked_telemetry("genome_mono", "p99_latency", 120.0)
        runtime.ingest_watermarked_telemetry("genome_micro", "p99_latency", 45.0)

        # 4. CKB Learning (Phase 17)
        evidence = EmpiricalEvidence(
            experiment_id="exp_001", context="High-scale B2B",
            latency_ms=45.0, error_rate=0.01, outcome="survived")
        learning.record_outcome("Microservices_Pattern", evidence)

        assert learning.ckb["Microservices_Pattern"].confidence_score == 1.0

        # 5. Verify UEM Lineage (Phase 18.5)
        lineage = uem.get_lineage("genome_micro")
        assert any(e.event_type.value == "telemetry_ingested"
                   for e in lineage)

        # 6. Governance proof attached to agent events
        agent_events = uem.events_by_type(EventType.AGENT_CRITIQUE)
        assert len(agent_events) == 1
        assert agent_events[0].constitutional_proof.startswith("gov_proof_")

    def test_uem_is_append_only(self, ase_os):
        uem, *_ = ase_os
        before = uem.size
        uem.append(UEMEvent(
            event_type=EventType.SIMULATION_RUN, actor_id="Sim",
            target_id="isr_1", payload={"latency_ms": 5.0}))
        assert uem.size == before + 1
        assert len(uem.get_lineage("isr_1")) == 1
