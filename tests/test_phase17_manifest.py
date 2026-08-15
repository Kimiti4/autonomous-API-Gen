"""Phase 17 -- provenance manifest construction."""
from __future__ import annotations

import hashlib
from types import SimpleNamespace

from tiannara.application.materializer.provenance_builder import build_manifest
from tiannara.domain.models.capability_manifest import (
    BundleCapability,
    CapabilityManifest,
)
from tiannara.domain.models.compilation import CompilationResult
from tiannara.application.compiler.verification import BundleVerificationReport

STATEMENT = "Order Management"


def _manifest() -> CapabilityManifest:
    return CapabilityManifest(
        backend_id="fastapi_hexagonal",
        capabilities=[
            BundleCapability.BUILD,
            BundleCapability.TEST,
            BundleCapability.HEALTH_CHECK,
            BundleCapability.CONTAINERIZE,
        ],
        metadata={"language": "python", "framework": "fastapi"},
    )


def _outcome(ok: bool = True) -> SimpleNamespace:
    result = CompilationResult(
        backend_id="fastapi_hexagonal",
        system_name="order-management",
        files={"order-management/main.py": "x = 1"},
        capability_manifest=_manifest(),
    )
    report = BundleVerificationReport(ok=ok) if ok else BundleVerificationReport(
        ok=False, syntax_errors=["order-management/main.py: invalid syntax"]
    )
    return SimpleNamespace(status="success", result=result, verification_report=report)


def _report() -> SimpleNamespace:
    return SimpleNamespace(
        statement_hash=hashlib.sha256(STATEMENT.encode()).hexdigest(),
        isr_hash="isr-hash-1234",
        plan_id="plan-abc",
        outcomes=[_outcome(ok=True)],
    )


def test_manifest_carries_full_lineage():
    report = _report()
    manifest = build_manifest(report, report.outcomes, forced=False, build_id="b-1")
    assert manifest.schema_version == "1.0"
    assert manifest.build_id == "b-1"
    assert manifest.intent_hash == report.statement_hash
    assert manifest.isr_hash == report.isr_hash
    assert manifest.plan_id == report.plan_id
    assert manifest.backend_ids == ["fastapi_hexagonal"]
    assert manifest.verification.ok is True
    assert manifest.verification.forced is False
    assert manifest.capability_manifests[0].backend_id == "fastapi_hexagonal"
    assert manifest.capability_manifests[0].verification.ok is True
    serialized = manifest.model_dump_json()
    assert "order-management" in serialized


def test_manifest_forces_flag_when_force_supplied():
    report = _report()
    failing = SimpleNamespace(
        statement_hash="s",
        isr_hash="i",
        plan_id="p",
        outcomes=[SimpleNamespace(
            status="success",
            result=report.outcomes[0].result,
            verification_report=BundleVerificationReport(ok=False),
        )],
    )
    manifest = build_manifest(failing, failing.outcomes, forced=True, build_id="b-2")
    assert manifest.verification.forced is True
    assert manifest.verification.ok is False
    assert "forced_reason" in manifest.verification.details
    assert manifest.policy_name is None  # tree does not expose it

def test_manifest_aggregates_multiple_backends():
    r1 = _outcome(ok=True)
    r2 = _outcome(ok=True)
    merged_report = SimpleNamespace(
        statement_hash=hashlib.sha256(b"x").hexdigest(),
        isr_hash="isr-2",
        plan_id="plan-2",
        outcomes=[r1, r2],
    )
    manifest = build_manifest(merged_report, merged_report.outcomes, forced=False)
    assert manifest.backend_ids == ["fastapi_hexagonal"]
    assert len(manifest.capability_manifests) == 2
