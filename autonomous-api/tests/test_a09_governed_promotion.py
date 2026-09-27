from types import SimpleNamespace

import pytest

from app.engine.evolution import EvolutionEngine


class _Settings:
    GOVERNANCE_ENFORCEMENT_REQUIRED = True


class _Governance:
    def __init__(self, state):
        self.state = state

    async def materialize_candidate(self, _candidate_id):
        return self.state


@pytest.mark.asyncio
async def test_governance_denies_promotion_without_authorizing_decision(monkeypatch):
    state = SimpleNamespace(
        current_state="verified",
        latest_decision=lambda: None,
    )
    monkeypatch.setattr("app.engine.evolution.get_settings", lambda: _Settings())
    monkeypatch.setattr(
        "app.engine.evolution.get_governance", lambda: _Governance(state)
    )

    engine = EvolutionEngine()
    genome = SimpleNamespace(genome_id="candidate-denied")

    assert await engine._governance_allows_promotion(genome) is False


@pytest.mark.asyncio
async def test_governance_allows_promotion_only_after_authorizing_decision(monkeypatch):
    decision = SimpleNamespace(verdict="approve", authorizesTransition=True)
    state = SimpleNamespace(
        current_state="certified",
        latest_decision=lambda: decision,
    )
    monkeypatch.setattr("app.engine.evolution.get_settings", lambda: _Settings())
    monkeypatch.setattr(
        "app.engine.evolution.get_governance", lambda: _Governance(state)
    )

    engine = EvolutionEngine()
    genome = SimpleNamespace(genome_id="candidate-approved")

    assert await engine._governance_allows_promotion(genome) is True


def test_promotion_event_is_emitted_only_by_explicit_promotion_event():
    mapping = EvolutionEngine._EVENT_TYPE_MAP

    assert mapping["new_best"] == "evolution.stage_changed"
    assert mapping["candidate_promoted"] == "candidate.promoted"
    assert "candidate.promoted" not in mapping.values() or list(mapping.values()).count(
        "candidate.promoted"
    ) == 1
