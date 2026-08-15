import pytest

from constitutional_architecture.core.agents.base import (
    Agent, Critique, ObjectionSeverity,
)
from constitutional_architecture.core.agents.specialized import (
    DomainExpertAgent, SecurityEngineerAgent,
)
from constitutional_architecture.core.orchestrator.negotiation import (
    MultiAgentCoordinator, NegotiationFailure,
)


@pytest.fixture
def coordinator():
    return MultiAgentCoordinator(agents=[
        SecurityEngineerAgent(),
        DomainExpertAgent(),
    ])


class TestSecurityAgent:
    def test_security_agent_blocks_unclassified_pii(self, coordinator):
        raw_reqs = {
            "project_name": "HealthApp",
            "capabilities": [
                {"name": "Patient Records",
                 "description": "Store patient health records and SSNs",
                 "security_classification": "standard"},
            ],
        }

        refined_draft = coordinator.negotiate_intent(raw_reqs)

        assert refined_draft["capabilities"][0][
            "security_classification"] == "restricted"

    def test_security_agent_clean_capability_untouched(self, coordinator):
        raw_reqs = {
            "project_name": "TodoApp",
            "capabilities": [
                {"name": "Tasks",
                 "description": "Manage personal to-do items",
                 "security_classification": "standard"},
            ],
        }
        refined = coordinator.negotiate_intent(raw_reqs)
        assert refined["capabilities"][0][
            "security_classification"] == "standard"

    def test_draft_is_not_mutated_in_place(self, coordinator):
        raw_reqs = {
            "project_name": "HealthApp",
            "capabilities": [
                {"name": "Patient Records",
                 "description": "Store patient health records and SSNs",
                 "security_classification": "standard"},
            ],
        }
        coordinator.negotiate_intent(raw_reqs)
        assert raw_reqs["capabilities"][0][
            "security_classification"] == "standard"


class TestDomainAgent:
    def test_domain_agent_warns_on_god_blob(self, coordinator):
        raw_reqs = {
            "project_name": "MegaCorp",
            "data_domains": [
                {"name": "Everything",
                 "entities": [f"Entity_{i}" for i in range(15)]},
            ],
            "capabilities": [{"name": "DoStuff", "description": "Does stuff"}],
        }

        refined_draft = coordinator.negotiate_intent(raw_reqs)
        assert refined_draft is not None
        assert coordinator.round_log

    def test_domain_agent_small_domain_clean(self, coordinator):
        raw_reqs = {
            "project_name": "SmallCo",
            "data_domains": [
                {"name": "Billing", "entities": ["Invoice", "Payment"]},
            ],
            "capabilities": [{"name": "Bill", "description": "Bill users"}],
        }
        refined = coordinator.negotiate_intent(raw_reqs)
        assert refined["data_domains"][0]["name"] == "Billing"


class TestNegotiationProtocol:
    def test_negotiation_fails_on_unresolvable_fatal_flaw(self):
        class StubbornAgent(Agent):
            role: str = "Stubborn"

            def analyze(self, draft, context):
                return [Critique(
                    agent_role=self.role,
                    severity=ObjectionSeverity.FATAL,
                    message="I reject everything.",
                    proposed_directives=[],
                )]

        coord = MultiAgentCoordinator([StubbornAgent()])

        with pytest.raises(NegotiationFailure, match="Fatal flaws remain"):
            coord.negotiate_intent({"project_name": "Test"})

    def test_fatal_resolved_within_rounds(self, coordinator):
        """FATAL raised in round 1 is resolved by the directive; consensus
        is reached without exhausting the round budget."""
        raw_reqs = {
            "project_name": "FinApp",
            "capabilities": [
                {"name": "Payments",
                 "description": "Process credit card payments",
                 "security_classification": "standard"},
            ],
        }
        refined = coordinator.negotiate_intent(raw_reqs)
        assert refined["capabilities"][0][
            "security_classification"] == "restricted"
        assert len(coordinator.round_log) < coordinator.MAX_ROUNDS

    def test_agents_never_talk_to_each_other(self, coordinator):
        """Agents interact only with the draft; no agent references another."""
        from constitutional_architecture.core.agents.base import Agent
        assert not any(
            hasattr(a, "agents") or hasattr(a, "peer") for a in coordinator.agents
        )
