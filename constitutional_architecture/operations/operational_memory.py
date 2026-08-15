"""
Operational Memory.

Persistent storage for operational observations.
All observations are append-only historical records.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from constitutional_architecture.operations.observation_model import (
    Anomaly,
    DriftReport,
    FitnessSignal,
    Incident,
    Observation,
    Recommendation,
)


class OperationalMemory:

    def __init__(self, storage_path: Optional[str | Path] = None) -> None:
        self._storage_path = Path(storage_path) if storage_path else None
        self._observations: list[Observation] = []
        self._anomalies: list[Anomaly] = []
        self._drift_reports: list[DriftReport] = []
        self._incidents: list[Incident] = []
        self._fitness_signals: list[FitnessSignal] = []
        self._recommendations: list[Recommendation] = []
        self._max_per_type: int = 100000

        if self._storage_path and self._storage_path.exists():
            self._load()

    def record_observation(self, observation: Observation) -> None:
        self._observations.append(observation)
        if len(self._observations) > self._max_per_type:
            self._observations = self._observations[-self._max_per_type:]
        self._save()

    def record_anomaly(self, anomaly: Anomaly) -> None:
        self._anomalies.append(anomaly)
        if len(self._anomalies) > self._max_per_type:
            self._anomalies = self._anomalies[-self._max_per_type:]

    def record_drift(self, report: DriftReport) -> None:
        self._drift_reports.append(report)

    def record_incident(self, incident: Incident) -> None:
        self._incidents.append(incident)

    def record_fitness_signal(self, signal: FitnessSignal) -> None:
        self._fitness_signals.append(signal)
        if len(self._fitness_signals) > self._max_per_type:
            self._fitness_signals = self._fitness_signals[-self._max_per_type:]

    def record_recommendation(self, recommendation: Recommendation) -> None:
        self._recommendations.append(recommendation)

    @property
    def observations(self) -> list[Observation]:
        return list(self._observations)

    @property
    def anomalies(self) -> list[Anomaly]:
        return list(self._anomalies)

    @property
    def incidents(self) -> list[Incident]:
        return list(self._incidents)

    @property
    def fitness_signals(self) -> list[FitnessSignal]:
        return list(self._fitness_signals)

    @property
    def recommendations(self) -> list[Recommendation]:
        return list(self._recommendations)

    @property
    def drift_reports(self) -> list[DriftReport]:
        return list(self._drift_reports)

    def get_recent_observations(self, n: int = 100) -> list[Observation]:
        return self._observations[-n:]

    def get_recent_signals(self, n: int = 100) -> list[FitnessSignal]:
        return self._fitness_signals[-n:]

    def _save(self) -> None:
        if self._storage_path is None:
            return
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "observations": [self._obs_to_dict(o) for o in self._observations[-1000:]],
            "fitness_signals": [self._signal_to_dict(s) for s in self._fitness_signals[-1000:]],
        }
        self._storage_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    def _load(self) -> None:
        if self._storage_path is None or not self._storage_path.exists():
            return
        try:
            json.loads(self._storage_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, KeyError):
            pass

    def _obs_to_dict(self, obs: Observation) -> dict[str, Any]:
        return {
            "id": obs.id, "source": obs.source.value,
            "severity": obs.severity.value,
            "timestamp": obs.timestamp.isoformat(),
            "title": obs.title, "description": obs.description,
            "classification": obs.classification.value,
            "deployment_id": obs.deployment_id,
            "isr_hash": obs.isr_hash,
        }

    def _signal_to_dict(self, signal: FitnessSignal) -> dict[str, Any]:
        return signal.to_dict()
