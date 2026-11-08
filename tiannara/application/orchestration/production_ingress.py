"""Governed full-stack production ingress — delegates to CP055 canonical authority."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from certification.orchestration.authority import run_canonical_full_stack
from certification.orchestration.boundaries import assert_direct_compile_boundary
from certification.orchestration.contract import DirectCompileBoundary, OrchestrationLifecycleState
from certification.orchestration.workload_registry import ALL_WORKLOAD_IDS, get_workload_spec
from tiannara.application.governance.production_boundary import governed_production_enabled


class GovernedFullStackIngressUnavailable(RuntimeError):
    """Raised when trusted evidence / governance stores are not configured."""


@dataclass(frozen=True)
class IngressStatus:
    governed_production_enabled: bool
    trusted_evidence_ledger: str
    governance_candidate_store: str
    canonical_authority_id: str
    registered_workloads: tuple[str, ...]


def ingress_status() -> IngressStatus:
    from certification.orchestration.authority import FullStackOrchestrationAuthority

    return IngressStatus(
        governed_production_enabled=governed_production_enabled(),
        trusted_evidence_ledger=os.getenv("ESAP_TRUSTED_EVIDENCE_LEDGER", "").strip(),
        governance_candidate_store=os.getenv("ESAP_GOVERNANCE_CANDIDATE_STORE", "").strip(),
        canonical_authority_id=FullStackOrchestrationAuthority.AUTHORITY_ID,
        registered_workloads=ALL_WORKLOAD_IDS,
    )


def require_ingress_paths(
    *,
    evidence_registry_path: str | None = None,
    governance_store_path: str | None = None,
) -> tuple[str, str]:
    tev = (evidence_registry_path or os.getenv("ESAP_TRUSTED_EVIDENCE_LEDGER", "")).strip()
    gov = (governance_store_path or os.getenv("ESAP_GOVERNANCE_CANDIDATE_STORE", "")).strip()
    if not tev or not gov:
        raise GovernedFullStackIngressUnavailable("governed-full-stack-ingress-not-configured")
    if not governed_production_enabled():
        raise GovernedFullStackIngressUnavailable("governed-production-disabled")
    return tev, gov


def _idempotency_path(root: Path, key: str) -> Path:
    d = root / "idempotency"
    d.mkdir(parents=True, exist_ok=True)
    safe = key.replace("/", "_")[:128]
    return d / f"{safe}.json"


def resolve_idempotent_run(
    orchestration_store_path: str,
    idempotency_key: str,
) -> dict | None:
    path = _idempotency_path(Path(orchestration_store_path), idempotency_key)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _save_idempotent_run(orchestration_store_path: str, idempotency_key: str, payload: dict) -> None:
    path = _idempotency_path(Path(orchestration_store_path), idempotency_key)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def execute_governed_full_stack_ingress(
    workload_id: str,
    *,
    evidence_registry_path: str | None = None,
    governance_store_path: str | None = None,
    orchestration_store_path: str | None = None,
    idempotency_key: str | None = None,
    artifact_sha256_bind: str | None = None,
    populate_senior_dimensions: bool = False,
    isr_ingress_authority: str = "isr.core.revision",
    governed_lineage_ref: str = "",
    plan_binding_digest: str | None = None,
) -> dict:
    """Production ingress for governed full-stack requests."""
    if workload_id not in ALL_WORKLOAD_IDS:
        raise ValueError(f"orchestration-unknown-workload:{workload_id}")

    tev, gov = require_ingress_paths(
        evidence_registry_path=evidence_registry_path,
        governance_store_path=governance_store_path,
    )
    orun = orchestration_store_path or str(Path(gov).parent / "orchestration-runs")

    if idempotency_key:
        cached = resolve_idempotent_run(orun, idempotency_key)
        if cached is not None:
            if artifact_sha256_bind and cached.get("artifactSha256") != artifact_sha256_bind:
                raise ValueError("orchestration-artifact-binding-mismatch")
            return cached

    from certification.orchestration.implir_ingress_guard import (
        assert_trusted_orchestration_ingress,
    )

    assert_trusted_orchestration_ingress(
        isr_ingress_authority,
        governed_lineage_ref=governed_lineage_ref,
    )
    get_workload_spec(workload_id)
    report = run_canonical_full_stack(
        workload_id,
        evidence_registry_path=tev,
        governance_store_path=gov,
        orchestration_store_path=orun,
        populate_senior_dimensions=populate_senior_dimensions,
        isr_ingress_authority=isr_ingress_authority,
        governed_lineage_ref=governed_lineage_ref,
        plan_binding_digest=plan_binding_digest or "",
    )

    if artifact_sha256_bind and report.artifact_sha256 != artifact_sha256_bind:
        raise ValueError("orchestration-artifact-binding-mismatch")

    if report.state in {
        OrchestrationLifecycleState.CERTIFIED,
        OrchestrationLifecycleState.PUBLICATION_AUTHORIZED,
        OrchestrationLifecycleState.PUBLISHED,
    }:
        raise ValueError("orchestration-ingress-forbids-impersonating-certification")

    payload = {
        "authorityId": "tiannara.orchestration.full_stack.v1",
        "runId": report.run_id,
        "workloadId": report.workload_id,
        "candidateId": report.candidate_id,
        "lifecycleState": report.state.value,
        "governanceLifecycleState": report.governance_lifecycle_state,
        "isrProvenance": report.isr_provenance.value,
        "revisionId": report.revision_id,
        "artifactSha256": report.artifact_sha256,
        "canonicalContractDigest": report.canonical_contract_digest,
        "productAcceptance": report.product_acceptance.value,
        "certified": False,
        "publicationAuthorized": False,
        "blockers": list(report.blockers),
        "limitations": list(report.limitations),
        "evidenceIds": list(report.evidence_ids),
    }
    if idempotency_key:
        _save_idempotent_run(orun, idempotency_key, payload)
    return payload


def assert_subordinate_compile_boundary(workload_id: str) -> None:
    assert_direct_compile_boundary(
        DirectCompileBoundary(workload_id=workload_id, completes_lifecycle=False)
    )
