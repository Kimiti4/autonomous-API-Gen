"""Evolution Engine -> Lineage wiring (§10.3)."""
from app.core.lineage.commands import RecordCandidateOrigin, RecordEvolutionOperation, RecordFitnessEvaluation
from app.core.contracts.lineage import OriginSpec

async def on_candidate_created(lineage_subsystem, candidate_id: str, generation: int, isr_revision: str, origin_type: str, parent_ids: list[str]):
    cmd = RecordCandidateOrigin(
        candidateId=candidate_id,
        generation=generation,
        isrRevision=isr_revision,
        origin=OriginSpec(operationType=origin_type, parentCandidateIds=parent_ids, operationId=f"op-{candidate_id}", summary=f"{origin_type} for {candidate_id}"),
    )
    await lineage_subsystem.record_origin(cmd)

async def on_fitness_evaluated(lineage_subsystem, candidate_id: str, evaluation):
    from app.core.lineage.commands import RecordFitnessEvaluation
    await lineage_subsystem.record_fitness_evaluation(RecordFitnessEvaluation(candidateId=candidate_id, evaluation=evaluation))
