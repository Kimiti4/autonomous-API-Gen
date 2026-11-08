"""Workspace bridge for governed full-stack orchestration ingress (CP056)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from app.core.config import get_settings

_WORKSPACE = Path(__file__).resolve().parents[3]
if str(_WORKSPACE) not in sys.path:
    sys.path.insert(0, str(_WORKSPACE))

from tiannara.application.orchestration.production_ingress import (  # noqa: E402
    GovernedFullStackIngressUnavailable,
    execute_governed_full_stack_ingress,
    ingress_status,
)
from tiannara.application.orchestration.route_policy import policies_summary  # noqa: E402


def _sync_governed_env_from_settings() -> None:
    settings = get_settings()
    if settings.ESAP_GOVERNED_PRODUCTION:
        os.environ["ESAP_GOVERNED_PRODUCTION"] = "1"
    if settings.ESAP_TRUSTED_EVIDENCE_LEDGER.strip():
        os.environ["ESAP_TRUSTED_EVIDENCE_LEDGER"] = settings.ESAP_TRUSTED_EVIDENCE_LEDGER.strip()
    if settings.ESAP_GOVERNANCE_CANDIDATE_STORE.strip():
        os.environ["ESAP_GOVERNANCE_CANDIDATE_STORE"] = (
            settings.ESAP_GOVERNANCE_CANDIDATE_STORE.strip()
        )


def orchestration_ingress_status() -> dict:
    _sync_governed_env_from_settings()
    st = ingress_status()
    return {
        "governedProductionEnabled": st.governed_production_enabled,
        "trustedEvidenceLedger": st.trusted_evidence_ledger or None,
        "governanceCandidateStore": st.governance_candidate_store or None,
        "canonicalAuthorityId": st.canonical_authority_id,
        "registeredWorkloads": list(st.registered_workloads),
        "routePolicies": policies_summary(),
    }


def run_governed_full_stack(body) -> dict:
    _sync_governed_env_from_settings()
    from certification.orchestration.implir_ingress_guard import (
        assert_trusted_orchestration_ingress,
    )

    assert_trusted_orchestration_ingress(
        body.isr_ingress_authority,
        governed_lineage_ref=body.governed_lineage_ref,
    )
    settings = get_settings()
    return execute_governed_full_stack_ingress(
        body.workload_id,
        evidence_registry_path=settings.ESAP_TRUSTED_EVIDENCE_LEDGER.strip() or None,
        governance_store_path=settings.ESAP_GOVERNANCE_CANDIDATE_STORE.strip() or None,
        idempotency_key=body.idempotency_key or None,
        artifact_sha256_bind=body.artifact_sha256_bind or None,
        populate_senior_dimensions=body.populate_senior_dimensions,
        isr_ingress_authority=body.isr_ingress_authority,
        governed_lineage_ref=body.governed_lineage_ref,
        plan_binding_digest=body.plan_binding_digest or None,
    )
