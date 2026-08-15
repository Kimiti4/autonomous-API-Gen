"""
Tests for Phase 27 — Marketplace & Plugin Ecosystem.
"""

import pytest

from marketplace_plugins.dependencies import satisfies
from marketplace_plugins.engine import PluginEcosystemEngine
from marketplace_plugins.manifest import sign_manifest
from marketplace_plugins.models import (
    PluginCapability,
    PluginManifestISR,
    PluginStatus,
    PublisherIdentityISR,
    SandboxPolicyISR,
)
from marketplace_plugins.sandbox import SandboxViolation


def make_publisher() -> PublisherIdentityISR:
    return PublisherIdentityISR(
        id="publisher_1",
        name="Constitutional Plugin Publisher",
        public_key_ref="key:publisher_1",
    )


def make_manifest(
    name: str,
    capabilities: list[PluginCapability],
    version: str = "1.0.0",
    dependencies: dict[str, str] | None = None,
    sandbox_policy: SandboxPolicyISR | None = None,
) -> PluginManifestISR:
    manifest = PluginManifestISR(
        name=name,
        version=version,
        publisher_id="publisher_1",
        capabilities=capabilities,
        dependencies=dependencies or {},
        sandbox_policy=sandbox_policy or SandboxPolicyISR(),
        signature="",
        payload_hash="mock_payload_hash",
    )

    return sign_manifest(manifest)


def build_engine_with_publisher() -> PluginEcosystemEngine:
    engine = PluginEcosystemEngine()
    engine.register_publisher(make_publisher())
    return engine


def test_semver_constraints():
    assert satisfies("1.2.3", "*")
    assert satisfies("1.2.3", "1.2.3")
    assert satisfies("1.2.3", "^1.2.0")
    assert satisfies("1.2.3", "~1.2.0")
    assert satisfies("1.2.3", ">=1.0.0")
    assert satisfies("1.2.3", "<2.0.0")

    assert not satisfies("1.2.3", "^2.0.0")
    assert not satisfies("1.2.3", "~1.3.0")
    assert not satisfies("1.2.3", "1.2.4")
    assert not satisfies("1.2.3", ">2.0.0")


def test_low_risk_plugin_is_auto_approved():
    engine = build_engine_with_publisher()

    manifest = make_manifest(
        name="safe_ui_component",
        capabilities=[PluginCapability.UI_COMPONENT],
    )

    listing = engine.publish_plugin(manifest)

    assert listing.status == PluginStatus.APPROVED


def test_high_risk_plugin_requires_approval():
    engine = build_engine_with_publisher()

    manifest = make_manifest(
        name="compiler_backend",
        capabilities=[PluginCapability.COMPILER_BACKEND],
    )

    listing = engine.publish_plugin(manifest)

    assert listing.status == PluginStatus.PENDING_REVIEW

    approved = engine.approve_plugin(
        listing.id,
        approver_id="governance_admin",
    )

    assert approved.status == PluginStatus.APPROVED
    assert approved.approval_ref == "governance:governance_admin"


def test_dependency_resolution_and_installation():
    engine = build_engine_with_publisher()

    base_manifest = make_manifest(
        name="base_library",
        capabilities=[PluginCapability.UI_COMPONENT],
        version="1.2.3",
    )

    base_listing = engine.publish_plugin(base_manifest)
    engine.install_plugin(base_listing.id)

    dependent_manifest = make_manifest(
        name="dependent_plugin",
        capabilities=[PluginCapability.UI_COMPONENT],
        dependencies={
            "base_library": "^1.2.0",
        },
    )

    dependent_listing = engine.publish_plugin(dependent_manifest)
    installed = engine.install_plugin(dependent_listing.id)

    assert installed.status == PluginStatus.INSTALLED


def test_dependency_version_conflict_quarantines_plugin():
    engine = build_engine_with_publisher()

    base_manifest = make_manifest(
        name="base_library",
        capabilities=[PluginCapability.UI_COMPONENT],
        version="1.2.3",
    )

    base_listing = engine.publish_plugin(base_manifest)
    engine.install_plugin(base_listing.id)

    dependent_manifest = make_manifest(
        name="dependent_plugin",
        capabilities=[PluginCapability.UI_COMPONENT],
        dependencies={
            "base_library": "^2.0.0",
        },
    )

    dependent_listing = engine.publish_plugin(dependent_manifest)

    with pytest.raises(ValueError):
        engine.install_plugin(dependent_listing.id)

    refreshed = engine.get_listing(dependent_listing.id)

    assert refreshed.status == PluginStatus.QUARANTINED


def test_sandbox_blocks_unauthorized_isr_mutation():
    engine = build_engine_with_publisher()

    policy = SandboxPolicyISR(allow_isr_mutation=False)

    manifest = make_manifest(
        name="strict_plugin",
        capabilities=[PluginCapability.UI_COMPONENT],
        sandbox_policy=policy,
    )

    listing = engine.publish_plugin(manifest)
    engine.install_plugin(listing.id)

    def malicious_entrypoint(context):
        return context.mutate_isr("architecture", {"change": "unauthorized"})

    engine.register_entrypoint(manifest.id, malicious_entrypoint)

    with pytest.raises(SandboxViolation):
        engine.execute_plugin(listing.id)

    refreshed = engine.get_listing(listing.id)

    assert refreshed.status == PluginStatus.QUARANTINED


def test_sandbox_allows_permitted_actions():
    engine = build_engine_with_publisher()

    policy = SandboxPolicyISR(
        allow_isr_mutation=True,
        allow_network_access=True,
    )

    manifest = make_manifest(
        name="permitted_plugin",
        capabilities=[PluginCapability.TELEMETRY_ADAPTER],
        sandbox_policy=policy,
    )

    listing = engine.publish_plugin(manifest)
    engine.install_plugin(listing.id)

    def entrypoint(context):
        context.mutate_isr("telemetry", {"enabled": True})
        context.fetch_network("https://telemetry.example")
        return "ok"

    engine.register_entrypoint(manifest.id, entrypoint)

    result = engine.execute_plugin(listing.id)

    assert result["status"] == "success"
    assert result["isr_mutations"] == 1
    assert result["network_calls"] == 1


def test_revocation_cascades_to_dependents():
    engine = build_engine_with_publisher()

    base_manifest = make_manifest(
        name="core_library",
        capabilities=[PluginCapability.UI_COMPONENT],
        version="1.0.0",
    )

    base_listing = engine.publish_plugin(base_manifest)
    engine.install_plugin(base_listing.id)

    dependent_manifest = make_manifest(
        name="app_plugin",
        capabilities=[PluginCapability.UI_COMPONENT],
        dependencies={
            "core_library": "1.0.0",
        },
    )

    dependent_listing = engine.publish_plugin(dependent_manifest)
    engine.install_plugin(dependent_listing.id)

    record = engine.revoke_plugin(
        base_listing.id,
        reason="Security vulnerability discovered.",
        revoked_by="security_admin",
    )

    refreshed_base = engine.get_listing(base_listing.id)
    refreshed_dependent = engine.get_listing(dependent_listing.id)

    assert refreshed_base.status == PluginStatus.REVOKED
    assert refreshed_dependent.status == PluginStatus.QUARANTINED
    assert dependent_listing.id in record.affected_dependents


def test_tampered_manifest_is_rejected():
    engine = build_engine_with_publisher()

    manifest = make_manifest(
        name="original_plugin",
        capabilities=[PluginCapability.UI_COMPONENT],
    )

    # Tamper with the manifest after signing
    manifest.name = "tampered_plugin"

    with pytest.raises(ValueError):
        engine.publish_plugin(manifest)


def test_governance_kernel_delegates_approval():
    """Phase 28 Constitutional Governance Kernel is wired into the gateway."""
    from constitutional_architecture.governance import GovernanceKernel

    from marketplace_plugins.engine import GovernanceGateway

    engine = build_engine_with_publisher()
    engine.governance = GovernanceGateway(governance_kernel=GovernanceKernel())

    # The default kernel has no plugin-specific policy, so it returns
    # Decision.ALLOW -> the manifest is auto-approved through the kernel.
    manifest = make_manifest(
        name="kernel_approved_plugin",
        capabilities=[PluginCapability.UI_COMPONENT],
    )

    listing = engine.publish_plugin(manifest)

    assert listing.status == PluginStatus.APPROVED
    assert any("Auto-approved" in event for event in listing.audit_trail)


def test_governance_extensions_record_evidence_in_kernel_delegate():
    """Phase 28 GovernedKernel wrapper records evidence when enabled (opt-in)."""
    from constitutional_architecture.governance import GovernanceKernel
    from constitutional_architecture.governance.integration import GovernedKernel

    from marketplace_plugins.engine import GovernanceGateway

    engine = build_engine_with_publisher()
    engine.governance = GovernanceGateway(
        governance_kernel=GovernanceKernel(),
        use_governance_extensions=True,
    )

    manifest = make_manifest(
        name="ext_plugin", capabilities=[PluginCapability.UI_COMPONENT]
    )
    listing = engine.publish_plugin(manifest)

    assert listing.status == PluginStatus.APPROVED
    gateway = engine.governance
    assert isinstance(gateway.governance_kernel, GovernedKernel)
    assert gateway._evidence is not None
    assert len(gateway._evidence.entries) >= 1
    assert gateway._evidence.verify_chain()
