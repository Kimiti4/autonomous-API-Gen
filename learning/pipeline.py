"""
Telemetry and signal pipeline.
"""

from __future__ import annotations

from typing import List, Optional

from .models import LearningPolicy, LearningSignal, LearningSignalType, Severity, severity_rank
from .utils import deterministic_id


class SignalPipeline:
    """Ingests and stores normalized learning signals."""

    def __init__(self, policy: LearningPolicy | None = None) -> None:
        self.policy = policy or LearningPolicy()
        self.signals: List[LearningSignal] = []

    def ingest(self, signal: LearningSignal) -> LearningSignal:
        if not signal.id:
            signal.id = deterministic_id(
                "learning_signal",
                {
                    "source": signal.source,
                    "subject_ref": signal.subject_ref,
                    "signal_type": signal.signal_type.value,
                    "metric": signal.metric,
                    "value": signal.value,
                    "timestamp": signal.timestamp,
                },
            )

        self.signals.append(signal)

        return signal

    def ingest_batch(self, signals: List[LearningSignal]) -> int:
        for signal in signals:
            self.ingest(signal)

        return len(signals)

    def query(
        self,
        subject_ref: Optional[str] = None,
        signal_type: Optional[LearningSignalType] = None,
        min_severity: Optional[Severity] = None,
    ) -> List[LearningSignal]:
        results: List[LearningSignal] = []

        min_rank = severity_rank(min_severity) if min_severity else 0

        for signal in self.signals:
            if subject_ref and signal.subject_ref != subject_ref:
                continue

            if signal_type and signal.signal_type != signal_type:
                continue

            if severity_rank(signal.severity) < min_rank:
                continue

            results.append(signal)

        return results
