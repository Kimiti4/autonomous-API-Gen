"""Operational feedback port — technology-independent seam for runtime telemetry."""

from __future__ import annotations

from typing import Protocol


class OperationalObservation:
    """A single operational data point fed back to the evolution engine."""

    def __init__(
        self,
        *,
        dimension: str,
        value: float,
        source: str = "",
        timestamp: str = "",
    ) -> None:
        self.dimension = dimension
        self.value = value
        self.source = source
        self.timestamp = timestamp


class OperationalFeedback(Protocol):
    """Port: collect operational observations for genome refinement.

    Adapters implement this for Prometheus, Datadog, logs, etc.
    """

    def collect(self) -> list[OperationalObservation]: ...


class ReferenceOperationalFeedback:
    """In-memory reference adapter for tests and gate verification."""

    def __init__(self) -> None:
        self._observations: list[OperationalObservation] = []

    def add(self, obs: OperationalObservation) -> None:
        self._observations.append(obs)

    def collect(self) -> list[OperationalObservation]:
        return list(self._observations)
