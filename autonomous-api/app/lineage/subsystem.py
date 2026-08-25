"""LineageSubsystem — command handler (§3.1, §3.7).

Records the immutable causal history. Never decides, never gates.
Validates L-1..L-5 before appending; corrections are appended as new
facts (L-3) — no command mutates an existing lineage fact.
"""
from __future__ import annotations

from typing import Optional

from app.core.lineage.commands import (
    RecordCandidateOrigin,
    RecordDeployment,
    RecordEvolutionOperation,
    RecordFitnessEvaluation,
    RecordOperationalFeedback,
    RecordVerification,
)
from app.core.lineage.events import (
    CandidateOriginRecorded,
    DeploymentRecorded,
    EvolutionOperationRecorded,
    FitnessEvaluationRecorded,
    OperationalFeedbackRecorded,
    VerificationRecorded,
)
from app.core.lineage.invariants import (
    check_l1_isr_revision_required,
    check_l2_parent_cardinality,
    check_l4_referential_integrity,
    check_l5_origin_idempotency,
)
from app.lineage.aggregate import CandidateLineage


class LineageSubsystem:
    def __init__(self, *, event_store,
                 candidate_registry: Optional[object] = None,
                 graph_index: Optional[object] = None) -> None:
        self._events = event_store
        self._registry = candidate_registry
        self._graph = graph_index

    async def record_candidate_origin(self, cmd: RecordCandidateOrigin):
        events = await self._events.load(cmd.candidateId)

        # Invariants BEFORE append.
        check_l1_isr_revision_required(cmd.isrRevision)
        check_l2_parent_cardinality(cmd.origin)
        await check_l4_referential_integrity(
            cmd.origin, cmd.requirementIds, self._registry
        )
        check_l5_origin_idempotency(events)

        event = CandidateOriginRecorded(
            candidateId=cmd.candidateId,
            generation=cmd.generation,
            isrRevision=cmd.isrRevision,
            requirementIds=list(cmd.requirementIds),
            origin=cmd.origin,
        )
        await self._events.append(cmd.candidateId, [event])
        return event

    async def record_evolution_operation(self, cmd: RecordEvolutionOperation):
        event = EvolutionOperationRecorded(
            candidateId=cmd.candidateId, operation=cmd.operation
        )
        await self._events.append(cmd.candidateId, [event])
        return event

    async def record_fitness_evaluation(self, cmd: RecordFitnessEvaluation):
        event = FitnessEvaluationRecorded(
            candidateId=cmd.candidateId, evaluation=cmd.evaluation
        )
        await self._events.append(cmd.candidateId, [event])
        return event

    async def record_verification(self, cmd: RecordVerification):
        event = VerificationRecorded(
            candidateId=cmd.candidateId, verification=cmd.verification
        )
        await self._events.append(cmd.candidateId, [event])
        return event

    async def record_deployment(self, cmd: RecordDeployment):
        event = DeploymentRecorded(
            candidateId=cmd.candidateId, deployment=cmd.deployment
        )
        await self._events.append(cmd.candidateId, [event])
        return event

    async def record_operational_feedback(self, cmd: RecordOperationalFeedback):
        event = OperationalFeedbackRecorded(
            candidateId=cmd.candidateId, feedback=cmd.feedback
        )
        await self._events.append(cmd.candidateId, [event])
        return event

    # ---- materialization --------------------------------------------------

    async def materialize(self, candidate_id: str,
                          as_of: Optional[int] = None):
        """Point-in-time reconstruction is first-class (§6)."""
        events = await self._events.load(candidate_id)
        return CandidateLineage.fold(candidate_id, events, as_of=as_of)