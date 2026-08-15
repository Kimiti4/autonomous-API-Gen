"""Derive provenance manifests from compiler outputs (Phase 17).

Lives in the application layer so it may depend on ``application.compiler``
types. The manifest *models* are pure domain data (see
``tiannara/domain/models/provenance.py``).
"""
from __future__ import annotations

from typing import Any

from tiannara.application.compiler.project_compiler import (
    ProjectCompilationReport,
    ProjectOutcome,
)
from tiannara.application.compiler.verification import BundleVerificationReport
from tiannara.domain.models.compilation import CompilationResult
from tiannara.domain.models.provenance import (
    BackedManifest,
    ProvenanceManifest,
    VerificationManifest,
)


def _verification_for(outcome: ProjectOutcome, forced: bool) -> VerificationManifest:
    report = outcome.verification_report
    if report is None:
        ok = False
        details: dict[str, Any] = {"absent": True}
    else:
        ok = bool(report.ok)
        details = {
            "missing_files": list(report.missing_files),
            "syntax_errors": list(report.syntax_errors),
            "dependency_violations": list(report.dependency_violations),
        }
    return VerificationManifest(ok=ok, forced=forced, details=details)


def build_manifest(
    report: ProjectCompilationReport,
    outcomes: list[ProjectOutcome],
    *,
    forced: bool,
    policy_name: str | None = None,
    build_id: str | None = None,
) -> ProvenanceManifest:
    """Build the provenance manifest for a materialized project.

    ``outcomes`` are the successful, CompilationResult-bearing outcomes
    selected for materialization. ``policy_name`` is ``None`` unless the
    caller can supply it; the in-tree ``ProjectCompilationReport`` does not
    carry it, so the manifest records ``None`` when absent.
    """
    backed: list[BackedManifest] = []
    aggregate_ok = True
    backend_ids: list[str] = []
    for outcome in outcomes:
        result = outcome.result
        if not isinstance(result, CompilationResult):
            continue
        backend_ids.append(result.backend_id)
        verification = _verification_for(outcome, forced)
        if not verification.ok:
            aggregate_ok = False
        backed.append(
            BackedManifest(
                backend_id=result.backend_id,
                system_name=result.system_name,
                capability_manifest=result.capability_manifest.model_dump(mode="json"),
                verification=verification,
            )
        )
    return ProvenanceManifest(
        build_id=build_id or "",
        intent_hash=report.statement_hash,
        isr_hash=report.isr_hash,
        plan_id=report.plan_id,
        policy_name=policy_name,
        backend_ids=sorted(set(backend_ids)),
        capability_manifests=backed,
        verification=VerificationManifest(
            ok=aggregate_ok,
            forced=forced,
            details=(
                {"forced_reason": "verification bypassed via --force"}
                if forced
                else {}
            ),
        ),
    )


def verification_summary(report: BundleVerificationReport) -> dict[str, Any]:
    return {
        "ok": report.ok,
        "missing_files": list(report.missing_files),
        "syntax_errors": list(report.syntax_errors),
        "dependency_violations": list(report.dependency_violations),
    }
