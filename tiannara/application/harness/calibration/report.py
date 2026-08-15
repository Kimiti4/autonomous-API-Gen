"""Phase-31 calibration result types.

A ``CalibrationReport`` is a *certification artifact*, not a transient test
result: it carries per-backend outcomes plus the explicit gate semantics under
which "successful generation" was judged. Durable so Phase 38 / Phase 20 can
compare cohorts.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from tiannara.application.compiler.verification import BundleVerificationReport
from tiannara.domain.models.evidence import CertificationEvidence, TestRunResult


@dataclass(frozen=True)
class CalibrationOutcome:
    """One backend's result for one ISR in the corpus."""

    system_name: str
    isr_hash: str
    backend_id: str
    bundle_path: Path | None
    verification_report: BundleVerificationReport | None
    runtime_status: str  # "ran" | "skipped:toolchain_absent" | "skipped:no_test_command"
    test_run: TestRunResult | None
    ok: bool
    evidence: CertificationEvidence


@dataclass(frozen=True)
class CalibrationReport:
    """Aggregate certification verdict for a corpus x backends matrix."""

    corpus_size: int
    backends_tested: tuple[str, ...]
    outcomes: tuple[CalibrationOutcome, ...]
    success_rate: float
    runtime_coverage: float
    gate_semantics: str
    ledger_path: str

    @property
    def total(self) -> int:
        return len(self.outcomes)

    @property
    def passed(self) -> int:
        return sum(1 for o in self.outcomes if o.ok)
