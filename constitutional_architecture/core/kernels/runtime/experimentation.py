"""
ASE-OS Runtime Kernel: Experimentation & Telemetry Ingestion.

Manages A/B deployments (champion vs challenger genomes) and ingests
watermarked production telemetry, routing each metric to the correct
experiment bucket by its genetic watermark.

Constitutional Alignment:
- "Continuous Evolution": production is the truth; simulated fitness is
  only a hypothesis.
- Blast Radius Containment: challenger traffic is strictly bounded by the
  configured traffic_split.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from constitutional_architecture.core.kernels.engineering.uem import (
    EventType, UEMEvent, UniversalEngineeringMemory,
)


class Experiment(BaseModel):
    experiment_id: str
    champion_genome_id: str
    challenger_genome_id: str
    traffic_split: float  # e.g., 0.10 for 10% to challenger
    telemetry_champion: Dict[str, float] = Field(default_factory=dict)
    telemetry_challenger: Dict[str, float] = Field(default_factory=dict)


class ExperimentManager:
    def __init__(self, uem: UniversalEngineeringMemory) -> None:
        self.uem = uem
        self.active_experiments: Dict[str, Experiment] = {}

    def start_experiment(self, experiment: Experiment) -> None:
        self.active_experiments[experiment.experiment_id] = experiment
        self.uem.append(UEMEvent(
            event_type=EventType.EXPERIMENT_STARTED,
            actor_id="RuntimeKernel",
            target_id=experiment.experiment_id,
            payload={
                "champion": experiment.champion_genome_id,
                "challenger": experiment.challenger_genome_id,
                "traffic_split": experiment.traffic_split,
            },
        ))

    def ingest_watermarked_telemetry(self, genome_id: str, metric: str,
                                     value: float) -> None:
        """Route telemetry to the correct experiment bucket based on the
        genetic watermark."""
        for experiment in self.active_experiments.values():
            if genome_id == experiment.champion_genome_id:
                experiment.telemetry_champion[metric] = value
            elif genome_id == experiment.challenger_genome_id:
                experiment.telemetry_challenger[metric] = value

        self.uem.append(UEMEvent(
            event_type=EventType.TELEMETRY_INGESTED,
            actor_id="RuntimeKernel",
            target_id=genome_id,
            payload={"metric": metric, "value": value},
        ))

    def conclude_experiment(self, experiment_id: str) -> Optional[str]:
        """Return the winning genome id, or None while inconclusive."""
        experiment = self.active_experiments.get(experiment_id)
        if experiment is None:
            return None
        champion = experiment.telemetry_champion
        challenger = experiment.telemetry_challenger
        if not champion or not challenger:
            return None
        if "p99_latency" not in champion or "p99_latency" not in challenger:
            return None
        if champion["p99_latency"] <= challenger["p99_latency"]:
            return experiment.champion_genome_id
        return experiment.challenger_genome_id
