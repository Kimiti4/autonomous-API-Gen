"""CP067-R5 W08 — HTTP adversarial ImplIR ingress (Model C)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def governed_env(tmp_path, monkeypatch):
    import app.core.config as config_module

    ledger = tmp_path / "tev.jsonl"
    store = tmp_path / "gov"
    store.mkdir()
    monkeypatch.setenv("ESAP_GOVERNED_PRODUCTION", "1")
    monkeypatch.setenv("ESAP_TRUSTED_EVIDENCE_LEDGER", str(ledger))
    monkeypatch.setenv("ESAP_GOVERNANCE_CANDIDATE_STORE", str(store))
    config_module._settings = None


def test_orchestration_http_blocks_implir_authority(client, governed_env):
    response = client.post(
        "/api/v1/orchestration/full-stack/run",
        headers={"X-API-Key": "test-admin-key"},
        json={
            "workload_id": "payroll",
            "isr_ingress_authority": "autonomous-api.implementation_ir",
        },
    )
    assert response.status_code == 403
    payload = response.json()
    detail = str(payload.get("detail") or payload.get("message") or payload).lower()
    assert "implir" in detail or "blocked" in detail or "trusted-orchestration" in detail


def test_orchestration_http_accepts_isr_revision_authority(client, governed_env):
    response = client.post(
        "/api/v1/orchestration/full-stack/run",
        headers={"X-API-Key": "test-admin-key"},
        json={
            "workload_id": "orders",
            "isr_ingress_authority": "isr.core.revision",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body.get("planBindingDigest") or "plan" in str(body).lower()


def test_publication_http_blocks_implir_even_with_stores(client, governed_env):
    response = client.post(
        "/api/v1/publication/publish",
        headers={"X-API-Key": "test-admin-key"},
        json={
            "candidate_id": "x",
            "isr_hash": "a" * 64,
            "artifact_sha256": "b" * 64,
            "source_revision": "rev",
            "artifact_manifest_digest": "c" * 64,
            "certification_id": "cert",
            "deployment_ref": "dep",
            "isr_ingress_authority": "autonomous-api.implementation_ir",
        },
    )
    assert response.status_code == 403
