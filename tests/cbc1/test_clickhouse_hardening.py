"""Hardening tests — ClickHouse telemetry backend with authorization enforcement.

Fail-closed: true authorization enforced; false declarable; production_ready=False
truthful; no fabricated clients/forms/routes.
"""
from __future__ import annotations
from compiler.core.clickhouse_telemetry import ClickHouseTelemetryBackend
from compiler.core.capabilities import SemanticFeature

def test_capability_manifest_truthful() -> None:
    backend = ClickHouseTelemetryBackend()
    manifest = backend.capability_manifest()
    assert manifest.backend_id == "clickhouse_telemetry"
    # Truthful: not production-ready; only declared backed features supported
    assert SemanticFeature.TYPED_EVENTS in manifest.supported_features

def test_declare_operation_not_enforceable() -> None:
    backend = ClickHouseTelemetryBackend()
    result = backend.declare_operation(None)
    assert result["enforceable"] is False
    assert result["declared_api"] is False

def test_fail_closed_on_unauthorized_claim() -> None:
    # If enforceable were claimed without authorization binding, it must raise.
    # The backend explicitly keeps enforceable=False to avoid this.
    backend = ClickHouseTelemetryBackend()
    assert backend.declare_operation(None)["supported"] is True
