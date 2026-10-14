"""Source-bound certification must reject policy drift and preserve UNKNOWN."""
import pytest

from tiannara.application.compiler.obligation_projection import project_requirement_graph
from tiannara.application.compiler.source_bound_certification import certify_source_bound_projection
from tiannara.application.compiler.trusted_obligation_evidence import TrustedObligationSuitePolicy
from tiannara.domain.models.compiler_obligation import Disposition
from tiannara.domain.models.requirement_graph import RequirementGraph, RequirementKind, RequirementNode
from tiannara.domain.models.system_model import Priority


class CountingStore:
    def __init__(self):
        self.reads = []

    def read(self, evidence_ref):
        self.reads.append(evidence_ref)
        return None


def source_graph():
    return RequirementGraph(
        graph_id="generic-app-v1",
        nodes=[
            RequirementNode(
                id="security.tenant-scope",
                kind=RequirementKind.CONSTRAINT,
                statement="Every data operation is scoped to the authorized tenant.",
                priority=Priority.MUST,
                acceptance_criteria=["Cross-tenant access is rejected."],
            )
        ],
    )


def policy(required_ids):
    return TrustedObligationSuitePolicy(
        suite_id="generic-app-suite-v1",
        required_obligation_ids=tuple(required_ids),
        expected_consumer_bindings={item: "runtime-consumer@v1" for item in required_ids},
        required_scenario_ids={item: ("cross-tenant-access-denied",) for item in required_ids},
    )


def test_source_bound_bridge_rejects_policy_omission_before_evidence_reads():
    graph = source_graph()
    projection = project_requirement_graph(graph)
    store = CountingStore()
    with pytest.raises(ValueError, match="do not exactly match the source projection"):
        certify_source_bound_projection(
            graph,
            projection,
            policy=policy(()),
            evidence_store=store,
            trusted_hmac_keys={},
            allowed_runner_ids=frozenset(),
        )
    assert store.reads == []


def test_source_bound_bridge_never_upgrades_unimplemented_obligation_to_pass():
    graph = source_graph()
    projection = project_requirement_graph(graph)
    required = projection.required_obligation_ids
    store = CountingStore()
    verdict = certify_source_bound_projection(
        graph,
        projection,
        policy=policy(required),
        evidence_store=store,
        trusted_hmac_keys={},
        allowed_runner_ids=frozenset(),
    )
    assert verdict.disposition is Disposition.UNKNOWN
    assert not verdict.ok
    assert verdict.required_obligations == required
    assert store.reads == []


def test_source_bound_bridge_rejects_projection_from_another_graph():
    graph = source_graph()
    projection = project_requirement_graph(graph)
    other = source_graph()
    other.graph_id = "different-app-v1"
    with pytest.raises(ValueError, match="does not match the active requirement graph"):
        certify_source_bound_projection(
            other,
            projection,
            policy=policy(projection.required_obligation_ids),
            evidence_store=CountingStore(),
            trusted_hmac_keys={},
            allowed_runner_ids=frozenset(),
        )
