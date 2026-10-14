from __future__ import annotations

import pytest

from tiannara.application.evolution.ledger import EvolutionLedger
from tiannara.application.publication.deployment_handoff import handoff_to_deployment
from tiannara.application.publication.repository_publisher_contract import (
    SystemDeploymentBundle,
    publish_bundle,
)
from tiannara.application.publication.uber_for_boats import run_uber_for_boats


def test_deployment_handoff_never_claims_success_without_provider_evidence():
    result = handoff_to_deployment("https://example.invalid/repository")

    assert result["status"] == "BLOCKED_NO_EVIDENCE"
    assert result["ci"] == "unknown"
    assert result["deployed"] is None
    assert result["health"] == "unknown"
    assert result["telemetry"] == "unknown"
    assert result["verified"] is False
    assert len(result["blockers"]) == 4


def test_deployment_handoff_requires_repository_reference():
    with pytest.raises(ValueError, match="repo_url"):
        handoff_to_deployment("")


def test_publisher_rejects_missing_certification_evidence_refs():
    bundle = SystemDeploymentBundle(
        isr_hash="isr-hash",
        artifact_hash="artifact-hash",
        certification_refs=(),
        deployment_ref="deployment-ref",
    )

    with pytest.raises(ValueError, match="no certification evidence references"):
        publish_bundle(bundle, provider=None, ledger=None, certification_gate=None)


def test_uber_for_boats_does_not_mint_its_own_certification_claim():
    result = run_uber_for_boats(ledger=EvolutionLedger())

    assert result["status"] == "BLOCKED_NO_CERTIFICATION_EVIDENCE"
    assert result["published"] is False
    assert result["verified"] is False
    assert "repo_url" not in result
    assert any("demo-created CERTIFIED event is not evidence" in item for item in result["blockers"])
