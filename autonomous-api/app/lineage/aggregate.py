"""CandidateLineage aggregate — the fold of a candidate's lineage event
log. Pure; no storage or framework imports.

Temporal model: materialize(candidate_id, as_of=N) folds the first N
events — point-in-time reconstruction is first-class (§6).
"""
from __future__ import annotations

from typing import Optional

from app.core.contracts.lineage import CandidateLineageState


class CandidateLineage:
    """Append-only aggregate. Each event appends a fact; the fold is the
    materialized lineage."""

    @staticmethod
    def fold(candidate_id: str, events: list,
             as_of: Optional[int] = None) -> CandidateLineageState:
        if as_of is not None:
            events = events[:as_of]

        state = CandidateLineageState(
            candidateId=candidate_id, generation=0, isrRevision=""
        )
        for event in events:
            name = type(event).__name__
            if name == "CandidateOriginRecorded":
                state = state.model_copy(
                    update={
                        "generation": event.generation,
                        "isrRevision": event.isrRevision,
                        "requirementIds": list(event.requirementIds),
                        "origin": event.origin,
                    }
                )
            elif name == "EvolutionOperationRecorded":
                state = state.model_copy(
                    update={
                        "operations": state.operations + [event.operation]
                    }
                )
            elif name == "FitnessEvaluationRecorded":
                state = state.model_copy(
                    update={
                        "evaluations": state.evaluations + [event.evaluation]
                    }
                )
            elif name == "VerificationRecorded":
                state = state.model_copy(
                    update={
                        "verifications": state.verifications
                        + [event.verification]
                    }
                )
            elif name == "DeploymentRecorded":
                state = state.model_copy(
                    update={
                        "deployments": state.deployments + [event.deployment]
                    }
                )
            elif name == "OperationalFeedbackRecorded":
                state = state.model_copy(
                    update={"feedback": state.feedback + [event.feedback]}
                )
        return state