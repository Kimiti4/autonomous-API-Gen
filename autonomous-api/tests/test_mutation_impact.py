"""Tests for Bucket 3.8 project-wide mutation impact intelligence."""

import pytest

from app.engine.mutation_impact import MutationImpactEngine, MutationRequest, ProjectNode


def node(node_id, layer, obligations=(), verifications=()):
    return ProjectNode(
        node_id=node_id,
        layer=layer,
        obligation_ids=tuple(obligations),
        verification_ids=tuple(verifications),
    )


def engine():
    return MutationImpactEngine(
        project_id="p1",
        nodes=[
            node("req", "requirement", ["REQ-1"], ["V-REQ"]),
            node("api", "api", ["REQ-1"], ["V-API"]),
            node("backend", "backend", ["REQ-1"], ["V-BE"]),
            node("frontend", "frontend", ["REQ-1"], ["V-FE"]),
            node("docs", "documentation", ["DOC-1"], ["V-DOC"]),
        ],
        dependencies=[
            ("api", "req"),
            ("backend", "api"),
            ("frontend", "api"),
            ("docs", "frontend"),
        ],
    )


def test_transitive_impact_is_computed_before_mutation():
    plan = engine().plan(
        MutationRequest(
            mutation_id="M-1",
            target_node_ids=("api",),
            reason="change API contract",
        )
    )

    assert plan.target_node_ids == ("api",)
    assert plan.direct_impact_node_ids == ("backend", "frontend")
    assert plan.transitive_impact_node_ids == ("api", "backend", "docs", "frontend")
    assert plan.affected_layers == ("api", "backend", "documentation", "frontend")
    assert plan.affected_obligation_ids == ("DOC-1", "REQ-1")
    assert plan.required_verification_ids == ("V-API", "V-BE", "V-DOC", "V-FE")
    assert plan.safe_to_apply is False


def test_target_only_does_not_claim_downstream_safety():
    plan = engine().plan(
        MutationRequest(
            mutation_id="M-2",
            target_node_ids=("api",),
            reason="inspect isolated target",
            requested_scope="target-only",
        )
    )

    assert plan.transitive_impact_node_ids == ("api",)
    assert plan.direct_impact_node_ids == ()
    assert plan.safe_to_apply is False


def test_bounded_depth_is_explicitly_marked_unbounded_when_dependents_remain():
    plan = engine().plan(
        MutationRequest(
            mutation_id="M-3",
            target_node_ids=("req",),
            reason="change requirement",
            max_depth=1,
        )
    )

    assert plan.transitive_impact_node_ids == ("api", "req")
    assert plan.bounded is False


def test_deterministic_plan_digest():
    request = MutationRequest(
        mutation_id="M-4",
        target_node_ids=("api",),
        reason="same governed change",
    )
    first = engine().plan(request)
    second = engine().plan(request)

    assert first == second
    assert len(first.plan_digest) == 64


def test_unknown_target_fails_closed():
    with pytest.raises(ValueError, match="unknown-mutation-target"):
        engine().plan(
            MutationRequest(
                mutation_id="M-5",
                target_node_ids=("missing",),
                reason="change missing target",
            )
        )


def test_invalid_graph_rejects_self_dependency():
    with pytest.raises(ValueError, match="self-dependency-rejected"):
        MutationImpactEngine(
            project_id="p1",
            nodes=[node("a", "backend")],
            dependencies=[("a", "a")],
        )


def test_duplicate_node_rejected():
    with pytest.raises(ValueError, match="duplicate-node-id"):
        MutationImpactEngine(
            project_id="p1",
            nodes=[node("a", "backend"), node("a", "frontend")],
        )


def test_multiple_targets_are_order_independent():
    e = engine()
    a = e.plan(
        MutationRequest(
            mutation_id="M-6",
            target_node_ids=("api", "frontend"),
            reason="paired change",
        )
    )
    b = e.plan(
        MutationRequest(
            mutation_id="M-6",
            target_node_ids=("frontend", "api"),
            reason="paired change",
        )
    )

    assert a == b
