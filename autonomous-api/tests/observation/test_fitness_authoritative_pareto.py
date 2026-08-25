"""GAP-07 acceptance: /observation/fitness Pareto matches engine output."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_fitness_matches_engine_pareto(fitness_projector):
    """Dashboard must not recompute; verify projection == engine result."""
    report = await fitness_projector.project(generation=1)
    engine_frontier = set(report.paretoFrontierCandidateIds)
    flagged = {c.candidateId for c in report.candidates if c.isOnParetoFrontier}
    assert flagged == engine_frontier


@pytest.mark.asyncio
async def test_frontier_flagging_matches_engine_scores(fitness_projector):
    report = await fitness_projector.project(generation=1)
    # The rich candidate leads on fitness/performance/security; the poor
    # one leads on cost/complexity → both are legitimately non-dominated.
    by_id = {c.candidateId: c for c in report.candidates}
    assert len(by_id) == 2
    assert all(c.isOnParetoFrontier for c in by_id.values())
    best = max(by_id.values(), key=lambda c: c.scores["fitness"])
    assert best.isOnParetoFrontier
    assert best.scores["fitness"] > 0


@pytest.mark.asyncio
async def test_report_carries_contract_metadata_and_provenance(
    fitness_projector,
):
    report = await fitness_projector.project(generation=1)
    assert report.metadata.contractId == "platform.observation.fitness"
    assert report.metadata.schemaVersion == "1.0.0"
    assert len(report.provenance.contentHash) == 64
    assert report.provenance.sourceSubsystem == "evolution-engine"


@pytest.mark.asyncio
async def test_fitness_endpoint_returns_authoritative_report(
    client, auth_headers, dispatcher
):
    from app.engine.genome import Genome

    # Seed generation 1 genomes through the dispatcher stream (any payload;
    # the endpoint reads canonical state, not events).
    await dispatcher.emit(
        stream_id="fitness-stream",
        event_type="fitness.evaluated",
        payload={"generation": 1},
        correlation_id="run-f",
        generation=1,
    )
    resp = client.get(
        "/observation/fitness",
        params={"generation": 1},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["metadata"]["contractId"] == "platform.observation.fitness"
    assert isinstance(body["paretoFrontierCandidateIds"], list)
    for candidate in body["candidates"]:
        assert isinstance(candidate["isOnParetoFrontier"], bool)