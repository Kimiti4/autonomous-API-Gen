"""R2.10.7 milestone — the cross-backend conformance campaign.

Same ISR through every conformed backend. The semantic source must be
invariant; the artifacts are allowed — required — to diverge. This is the
prerequisite for Phase 31: mass generation is only meaningful once different
realizations are proven to preserve the same semantics. The question changes
from "does each backend pass?" to "do different realizations preserve the
same ISR semantics?".
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from constitutional_architecture.isr.semantics.projection import (
    semantic_content_hash,
)

from .backend_conformance import (
    BackendConformanceAdapter,
    BackendConformanceReport,
)


@dataclass(frozen=True)
class CrossBackendConformanceReport:
    isr_semantic_hash: str
    per_backend: Mapping[str, BackendConformanceReport]
    semantic_invariance_held: bool  # one semantic source across all backends
    artifact_divergence_count: int  # distinct realizations
    all_conform: bool


class CrossBackendConformanceCampaign:
    """Conform the same ISR through every adapter and prove the semantic
    source is invariant across the divergent realizations."""

    def run(
        self,
        isr: Any,
        adapters: Mapping[str, BackendConformanceAdapter],
        evaluator: Any,
        targets: Mapping[str, Any],
    ) -> CrossBackendConformanceReport:
        per_backend = {
            backend_id: evaluator.conform(adapter, isr, targets[backend_id])
            for backend_id, adapter in adapters.items()
        }
        for report in per_backend.values():
            evaluator.record_report(report)
        results = {
            backend_id: adapter.compile(isr, targets[backend_id])
            for backend_id, adapter in adapters.items()
        }
        semantic_sources = {result.isr_hash for result in results.values()}
        invariance = semantic_sources == {semantic_content_hash(isr)}
        return CrossBackendConformanceReport(
            isr_semantic_hash=semantic_content_hash(isr),
            per_backend=per_backend,
            semantic_invariance_held=invariance,
            artifact_divergence_count=len(
                {result.artifact_hash for result in results.values()}
            ),
            all_conform=all(report.conforms for report in per_backend.values()),
        )