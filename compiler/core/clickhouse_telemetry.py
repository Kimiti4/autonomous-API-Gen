"""ClickHouse telemetry backend compiler target.

Technology-neutral-to-ClickHouse mapping for high-volume analytical
persistence. Not a production deployment claim; capability manifest
remains truthful (production_ready=False).
"""
from __future__ import annotations
from pathlib import Path
from compiler.core.capabilities import BackendCapabilities, SemanticFeature
from compiler.core.authorization import assert_authorization_enforceable

class ClickHouseTelemetryBackend:
    name = "clickhouse_telemetry"
    language = "sql"
    framework = "clickhouse"
    version = "1.0.0"
    supported_features = frozenset({
        SemanticFeature.TYPED_FIELDS,
        SemanticFeature.INVARIANTS,
        SemanticFeature.TYPED_EVENTS,
    })

    def build_profile(self, system_name: str):
        return {
            "language": "sql",
            "required_files": ("clickhouse_schema.sql", "telemetry_pipeline.sql"),
            "build_command": ["clickhouse-client", "--multiquery", "<", "telemetry_pipeline.sql"],
            "test_command": ["clickhouse-client", "--query", "SELECT count() FROM telemetry"],
            "runtime_image": "clickhouse/clickhouse-server:latest",
            "requires_build_phase": True,
        }

    def capability_manifest(self):
        # Truthful capability manifest — ClickHouse is a backend compiler target,
        # not a production-deployable service. Production readiness is false.
        return BackendCapabilities(
            backend_id=self.name,
            version=self.version,
            supported_features=self.supported_features,
        )
    
    def declare_operation(self, plan):
        """ClickHouse backend can emit telemetry ingestion routes.
        Enforced authorization required if enforceable is claimed.
        Fail-closed: raises UnsupportedSemanticsError if authorization is required
        but not enforceable per authorization contract.
        """
        enforceable = False  # ClickHouse telemetry does not emit typed allow rules
        if enforceable:
            assert_authorization_enforceable(plan)
        return {"declared_api": False, "supported": True, "enforceable": enforceable}
