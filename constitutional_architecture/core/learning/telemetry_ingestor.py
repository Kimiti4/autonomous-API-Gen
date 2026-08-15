"""
Phase 18 — Telemetry Ingestor.

Extracts genetic watermarks (evolution.genome_id, evolution.generation,
evolution.architecture_style) from production telemetry and aggregates
metrics by Genome, producing empirical GenomeTelemetryProfiles.

Constitutional Alignment:
- "Continuous Evolution": production metrics are the sensory input of the
  closed loop.
- Axiom VII (Auditability): profiles are append-only, sample-counted
  aggregations; every trace is counted.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class GenomeTelemetryProfile(BaseModel):
    """Aggregated real-world performance for a specific Genome generation."""

    genome_id: str
    generation: int = 0
    architecture_style: str = "unknown"

    p99_latency_ms: float = 0.0
    error_rate_percent: float = 0.0
    monthly_infrastructure_cost_usd: float = 0.0
    mttr_seconds: float = 0.0

    sample_size: int = 0  # Number of deployments/traces observed


class TelemetryIngestor:
    """
    Ingests raw OTEL/Prometheus data and groups it by evolutionary lineage.
    Traces without a genetic watermark are ignored — they carry no lineage.
    """

    WATERMARK_KEYS = (
        "evolution.genome_id",
        "evolution.generation",
        "evolution.architecture_style",
    )

    def __init__(self) -> None:
        self._profiles: Dict[str, GenomeTelemetryProfile] = {}

    def ingest_trace(self, trace_attributes: Dict[str, Any],
                     latency_ms: float, is_error: bool) -> None:
        """Process a single trace or metric data point."""
        genome_id = trace_attributes.get("evolution.genome_id")
        if not genome_id:
            return  # Ignore non-evolved or legacy telemetry

        profile = self._profiles.get(genome_id)
        if profile is None:
            profile = GenomeTelemetryProfile(
                genome_id=genome_id,
                generation=trace_attributes.get("evolution.generation") or 0,
                architecture_style=(
                    trace_attributes.get("evolution.architecture_style")
                    or "unknown"),
                p99_latency_ms=latency_ms,
                monthly_infrastructure_cost_usd=0.0,
            )
            self._profiles[genome_id] = profile

        profile.sample_size += 1
        profile.p99_latency_ms = max(profile.p99_latency_ms, latency_ms)
        if is_error:
            profile.error_rate_percent += (
                (1.0 / profile.sample_size) * 100)

    def ingest_infrastructure_cost(self, genome_id: str,
                                   monthly_cost_usd: float) -> None:
        """Populate cost data from infrastructure tags (Terraform watermark)."""
        if genome_id in self._profiles:
            self._profiles[genome_id].monthly_infrastructure_cost_usd = \
                monthly_cost_usd

    def ingest_mttr(self, genome_id: str, mttr_seconds: float) -> None:
        """Populate recovery-time data from incident timelines."""
        if genome_id in self._profiles:
            self._profiles[genome_id].mttr_seconds = mttr_seconds

    def get_empirical_data(self, genome_id: str) -> Optional[GenomeTelemetryProfile]:
        return self._profiles.get(genome_id)

    @property
    def profiles(self) -> Dict[str, GenomeTelemetryProfile]:
        return dict(self._profiles)

    @property
    def observed_genomes(self) -> int:
        return len(self._profiles)
