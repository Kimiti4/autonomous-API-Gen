"""Concrete projector exposing the EXISTING engine/fitness.py Pareto logic.

Constitutional note: isOnParetoFrontier is computed HERE (platform side)
by delegating to engine.fitness.pareto_front_analysis(). The dashboard is
forbidden from recomputing it.

This module imports the engine — that is its purpose: it is the adapter
between canonical evolution state and the observation contract.
"""
from __future__ import annotations

from typing import Any

from app.core.contracts.observations import (
    CandidateFitness,
    FitnessObjective,
    FitnessReport,
)
from app.core.contracts.provenance import (
    ContractMetadata,
    ObservationProvenance,
    now_utc,
)
from app.core.ids import content_hash
from app.observation.projectors.base import (
    CanonicalStateProvider,
    ProjectionContract,
)

# Import the existing platform capability we are exposing.
from app.engine.fitness import pareto_front_analysis  # noqa: E402
from app.engine.genome import Genome  # noqa: E402


class FitnessProjector:
    def __init__(
        self, *, provider: CanonicalStateProvider, source_revision: str
    ) -> None:
        self._provider = provider
        self._source_revision = source_revision

    async def project(self, generation: int) -> FitnessReport:
        record = await self._provider.get_generation(generation)

        # Bind the canonical generation-record schema to genomes.
        candidates, objectives = self._adapt(record)

        # Reuse the authoritative Pareto implementation.
        analysis = pareto_front_analysis(candidates)

        frontier_ids = sorted(
            g.genome_id for g, _scores in analysis["pareto_front"]
        )
        objective_names = analysis["objectives"]

        candidate_models = [
            CandidateFitness(
                candidateId=genome.genome_id,
                scores={k: float(v) for k, v in scores.items()},
                isOnParetoFrontier=genome.genome_id in frontier_ids,
            )
            for genome, scores in analysis["pareto_front"]
        ]
        # Include non-frontier candidates too (flagged False), so the
        # report covers every evaluated candidate for this generation.
        frontier_genome_ids = {g.genome_id for g, _ in analysis["pareto_front"]}
        seen = {c.candidateId for c in candidate_models}
        for genome in candidates:
            if genome.genome_id not in seen:
                candidate_models.append(
                    CandidateFitness(
                        candidateId=genome.genome_id,
                        scores={},  # per-candidate detail available via engine
                        isOnParetoFrontier=False,
                    )
                )

        body = {
            "generation": generation,
            "objectives": [o.model_dump() for o in objectives],
            "candidates": [c.model_dump() for c in candidate_models],
            "paretoFrontierCandidateIds": frontier_ids,
        }
        cid, ver = ProjectionContract.FITNESS
        provenance = ObservationProvenance(
            sourceRevision=self._source_revision,
            sourceSubsystem="evolution-engine",
            capturedAt=now_utc(),
            contentHash=content_hash(body),
        )
        return FitnessReport(
            metadata=ContractMetadata(contractId=cid, schemaVersion=ver),
            provenance=provenance,
            generation=generation,
            evaluatedAt=now_utc().isoformat(),
            objectives=objectives,
            candidates=candidate_models,
            paretoFrontierCandidateIds=frontier_ids,
        )

    @staticmethod
    def _adapt(record: Any):
        """Bind the canonical generation-record schema here.

        Accepts either:
          - an iterable of genome-data dicts (GenomeRecord.genome_data), or
          - an iterable of records carrying {"genome_data": {...}, ...}.
        Returns (genomes, objectives) ready for pareto_front_analysis().
        """
        genomes = []
        for i, item in enumerate(record):
            data = item.get("genome_data") if isinstance(item, dict) else item
            if not isinstance(data, dict):
                raise TypeError(
                    "Generation record %d is not a genome mapping" % i
                )
            genomes.append(Genome(data))

        # All engine objective scores are normalised 0..1, higher=better.
        objectives = [
            FitnessObjective(dimension=d, direction="maximize",
                             normalization="0..1")
            for d in ("fitness", "cost", "performance", "security", "complexity")
        ]
        return genomes, objectives