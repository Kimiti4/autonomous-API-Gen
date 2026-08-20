"""R2.10.32.9 — Operational evidence: the observability surface, measured
as present/absent evidence, never as a score.

Expands Operational Quality from deployment-posture markers to the full
observability surface the constitution's 'Observability by Design'
requires: structured logging, metrics, tracing, health checks, readiness
checks, and audit events. Each surface item is measured as present or
absent — evidence for the operational gate, never a composite score.
"""
from tiannara.application.quality.metric_analyzers import (
    MetricMeasurement,
    measurement_evidence_ref,
)

__all__ = ["OperationalEvidenceAnalyzer"]


class OperationalEvidenceAnalyzer:
    """The observability surface, measured as present/absent evidence."""

    OBSERVABILITY_SURFACE: tuple[str, ...] = (
        "structured_logging",
        "metrics",
        "distributed_tracing",
        "health_checks",
        "readiness_checks",
        "audit_events",
    )

    analyzer_id = "operational_evidence"
    analyzer_version = "1.0.0"

    def measure(self, artifact) -> tuple[MetricMeasurement, ...]:
        surface = artifact.get("observability", {})
        measurements = []
        for item in self.OBSERVABILITY_SURFACE:
            if surface.get(item):
                measurements.append(
                    MetricMeasurement(
                        metric_id=item,
                        analyzer_id=self.analyzer_id,
                        analyzer_version=self.analyzer_version,
                        artifact_identity=artifact["provenance"][
                            "artifact_hash"
                        ],
                        value=1.0,
                        evidence_refs=(
                            measurement_evidence_ref(artifact, item),
                        ),
                    )
                )
        return tuple(measurements)