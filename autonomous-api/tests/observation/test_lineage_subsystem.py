"""Lineage subsystem write acceptance: L-1..L-6 + temporal reconstruction."""
from __future__ import annotations

import pytest

from app.core.contracts.lineage import (
    DeploymentLineage,
    EvolutionOperation,
    FitnessEvaluationLineage,
    OriginSpec,
    VerificationLineage,
)
from app.core.lineage.commands import (
    RecordCandidateOrigin,
    RecordDeployment,
    RecordEvolutionOperation,
    RecordFitnessEvaluation,
    RecordVerification,
)
from app.core.lineage.invariants import LineageInvariantError
from app.lineage.adapters.memory import (
    InMemoryLineageEventStore,
    InMemoryLineageGraphIndex,
)
from app.lineage.subsystem import LineageSubsystem


class _Registry:
    """L-4 referential-integrity stub."""

    def __init__(self, candidates=(), requirements=()):
        self._candidates = set(candidates)
        self._requirements = set(requirements)

    async def candidate_exists(self, candidate_id: str) -> bool:
        return candidate_id in self._candidates

    async def requirement_exists(self, requirement_id: str) -> bool:
        return requirement_id in self._requirements


def _genesis_origin():
    return OriginSpec(
        operationType="genesis", operationId="op-1", summary="seeded"
    )


def _mutation_origin():
    return OriginSpec(
        operationType="mutation", parentCandidateIds=["p1"],
        operationId="op-2", summary="mutated from p1",
    )


def _subsystem(registry=None):
    events = InMemoryLineageEventStore()
    lineage = LineageSubsystem(
        event_store=events, candidate_registry=registry
    )
    return lineage, events


# ---- L-1 ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_l1_requires_isr_revision():
    lineage, _e = _subsystem()
    from pydantic import ValidationError
    with pytest.raises((LineageInvariantError, ValidationError)):
        await lineage.record_candidate_origin(RecordCandidateOrigin(
            candidateId="c1", generation=0, isrRevision="",
            origin=_genesis_origin(),
        ))


# ---- L-2 ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_l2_genesis_requires_zero_parents():
    lineage, _e = _subsystem()
    origin = OriginSpec(
        operationType="genesis", parentCandidateIds=["p1"],
        operationId="op-1", summary="bad genesis",
    )
    with pytest.raises(LineageInvariantError, match="L-2"):
        await lineage.record_candidate_origin(RecordCandidateOrigin(
            candidateId="c1", generation=0, isrRevision="rev-1",
            origin=origin,
        ))


@pytest.mark.asyncio
async def test_l2_non_genesis_requires_parent():
    lineage, _e = _subsystem()
    origin = OriginSpec(
        operationType="mutation", operationId="op-2", summary="no parent",
    )
    with pytest.raises(LineageInvariantError, match="L-2"):
        await lineage.record_candidate_origin(RecordCandidateOrigin(
            candidateId="c1", generation=0, isrRevision="rev-1",
            origin=origin,
        ))


# ---- L-4 ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_l4_rejects_unknown_parent():
    registry = _Registry(requirements={"req-1"})
    lineage, _e = _subsystem(registry)
    with pytest.raises(LineageInvariantError, match="L-4"):
        await lineage.record_candidate_origin(RecordCandidateOrigin(
            candidateId="c1", generation=0, isrRevision="rev-1",
            requirementIds=["req-1"], origin=_mutation_origin(),
        ))


@pytest.mark.asyncio
async def test_l4_rejects_unknown_requirement():
    registry = _Registry(candidates={"p1"})
    lineage, _ = _subsystem(registry)
    with pytest.raises(LineageInvariantError, match="L-4"):
        await lineage.record_candidate_origin(RecordCandidateOrigin(
            candidateId="c1", generation=0, isrRevision="rev-1",
            requirementIds=["unknown"], origin=_mutation_origin(),
        ))


# ---- L-5 ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_l5_origin_issued_once():
    lineage, _ = _subsystem()
    await lineage.record_candidate_origin(RecordCandidateOrigin(
        candidateId="c1", generation=0, isrRevision="rev-1",
        origin=_genesis_origin(),
    ))
    with pytest.raises(LineageInvariantError, match="L-5"):
        await lineage.record_candidate_origin(RecordCandidateOrigin(
            candidateId="c1", generation=1, isrRevision="rev-2",
            origin=_genesis_origin(),
        ))


# ---- happy path + temporal reconstruction -----------------------------------

@pytest.mark.asyncio
async def test_record_and_materialize_lineage():
    lineage, _ = _subsystem()
    await lineage.record_candidate_origin(RecordCandidateOrigin(
        candidateId="c1", generation=0, isrRevision="rev-1",
        requirementIds=["req-1"], origin=_genesis_origin(),
    ))
    await lineage.record_fitness_evaluation(RecordFitnessEvaluation(
        candidateId="c1",
        evaluation=FitnessEvaluationLineage(
            evaluationId="ev-1", generation=1, fitnessScore=0.9,
            objectiveScores={"cost": 0.8}, evaluatedAt="t1",
        ),
    ))
    await lineage.record_deployment(RecordDeployment(
        candidateId="c1",
        deployment=DeploymentLineage(
            deploymentId="dep-1", target="k8s", deployedBy="devops",
            deployedAt="t2",
        ),
    ))
    state = await lineage.materialize("c1")
    assert state.isrRevision == "rev-1"
    assert state.generation == 0
    assert len(state.evaluations) == 1
    assert len(state.deployments) == 1


@pytest.mark.asyncio
async def test_temporal_reconstruction_as_of():
    lineage, _ = _subsystem()
    await lineage.record_candidate_origin(RecordCandidateOrigin(
        candidateId="c1", generation=0, isrRevision="rev-1",
        origin=_genesis_origin(),
    ))
    await lineage.record_evolution_operation(RecordEvolutionOperation(
        candidateId="c1",
        operation=EvolutionOperation(
            operationId="op-e1", operationType="mutation", generation=1, summary="refine",
            occurredAt="t1",
        ),
    ))
    full = await lineage.materialize("c1")
    assert len(full.operations) == 1
    # Point-in-time reconstruction BEFORE the op was recorded.
    earlier = await lineage.materialize("c1", as_of=1)
    assert len(earlier.operations) == 0
    assert earlier.isrRevision == "rev-1"


# ---- L-3 append-only + graph index ------------------------------------------

@pytest.mark.asyncio
async def test_lineage_is_append_only_immutable():
    lineage, events = _subsystem()
    await lineage.record_candidate_origin(RecordCandidateOrigin(
        candidateId="c1", generation=0, isrRevision="rev-1",
        origin=_genesis_origin(),
    ))
    before = await events.load("c1")
    # Recording a new fact never mutates existing facts.
    await lineage.record_verification(RecordVerification(
        candidateId="c1",
        verification=VerificationLineage(
            verificationId="v-1", verifiedBy="qa", verdict="pass",
            verifiedAt="t3",
        ),
    ))
    after = await events.load("c1")
    assert len(after) == len(before) + 1


@pytest.mark.asyncio
async def test_graph_ancestors_and_children():
    store = InMemoryLineageEventStore()

    async def record(cid, parents):
        lineage = LineageSubsystem(event_store=store)
        origin = OriginSpec(
            operationType=("genesis" if not parents else "mutation"),
            parentCandidateIds=list(parents), operationId="op-" + cid,
            summary="origin",
        )
        await lineage.record_candidate_origin(RecordCandidateOrigin(
            candidateId=cid, generation=0, isrRevision="rev-1",
            origin=origin,
        ))

    await record("a", [])
    await record("b", ["a"])
    await record("c", ["a", "b"])
    graph = InMemoryLineageGraphIndex(store)
    assert sorted(await graph.ancestors_of("c")) == ["a", "b"]
    assert await graph.children_of("a") == ["b", "c"]