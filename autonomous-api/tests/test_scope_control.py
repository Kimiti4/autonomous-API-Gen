"""Tests for governed scope control."""

import pytest

from app.engine.scope_control import ScopeControlEngine, WorkProposal


@pytest.fixture
def engine():
    return ScopeControlEngine(
        project_id="p1",
        authoritative_obligation_ids={"REQ-1", "REQ-2"},
        known_obligation_ids={"DEF-1"},
    )


def test_authoritative_trace_is_required(engine):
    result = engine.decide(
        WorkProposal("W1", "implement required behavior", ("REQ-1",), authority="authoritative")
    )
    assert result.classification == "required"
    assert result.executable


def test_supporting_work_is_necessary_support(engine):
    result = engine.decide(
        WorkProposal("W2", "add required verification harness", ("REQ-2",), authority="derived")
    )
    assert result.classification == "necessary_support"
    assert result.executable


def test_untraced_advisory_work_is_not_executable(engine):
    result = engine.decide(
        WorkProposal("W3", "add a nice-to-have feature", authority="advisory")
    )
    assert result.classification == "advisory"
    assert not result.executable


def test_unscoped_derived_work_is_rejected(engine):
    result = engine.decide(
        WorkProposal("W4", "invent a new feature", authority="derived")
    )
    assert result.classification == "rejected"
    assert not result.executable


def test_unknown_obligation_fails_closed(engine):
    result = engine.decide(
        WorkProposal("W5", "work on unknown item", ("UNKNOWN",), authority="derived")
    )
    assert result.classification == "rejected"
    assert "fail-closed-on-unknown-scope" in result.reasons


def test_human_authorization_can_explicitly_authorize_new_required_work(engine):
    result = engine.decide(
        WorkProposal(
            "W6",
            "explicitly authorized change",
            authority="authoritative",
            explicitly_authorized=True,
        )
    )
    assert result.classification == "required"
    assert result.executable


def test_authoritative_claim_without_trace_is_rejected(engine):
    result = engine.decide(
        WorkProposal("W7", "pretend this is required", authority="authoritative")
    )
    assert result.classification == "rejected"


def test_digest_is_deterministic(engine):
    proposal = WorkProposal("W8", "support", ("REQ-1",), authority="derived")
    assert engine.decide(proposal) == engine.decide(proposal)
    assert len(engine.decide(proposal).digest) == 64
