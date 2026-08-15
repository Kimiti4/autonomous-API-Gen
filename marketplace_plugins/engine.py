"""
Core engine for the Marketplace & Plugin Ecosystem.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .dependencies import DependencyResolver
from .manifest import verify_manifest_signature
from .models import (
    MarketplaceListingISR,
    PluginCapability,
    PluginManifestISR,
    PluginStatus,
    PublisherIdentityISR,
    PublisherStatus,
    RevocationRecordISR,
    utcnow,
)
from .sandbox import (
    PluginEntrypoint,
    PluginExecutionContext,
    SandboxExecutor,
    SandboxViolation,
)


class GovernanceGateway:
    """
    Governance gateway for plugin approval.

    When wired to a Phase 28 ``GovernanceKernel`` (``governance_kernel``),
    approval decisions are delegated to the constitutional policy engine.
    Without a kernel, the gateway falls back to the reference high-risk
    capability heuristic.

    When ``use_governance_extensions`` is enabled (and a kernel is supplied),
    the kernel is wrapped in a Phase 28 ``GovernedKernel`` composition
    wrapper that records tamper-evident evidence for every decision and
    provides fail-closed amendment-authorisation. This is opt-in: the default
    gateway delegates to the raw kernel unchanged, preserving
    ``test_governance_kernel_delegates_approval``.
    """

    HIGH_RISK_CAPABILITIES = {
        PluginCapability.COMPILER_BACKEND,
        PluginCapability.EVOLUTION_MUTATOR,
        PluginCapability.VERIFICATION_ENGINE,
    }

    def __init__(
        self,
        governance_kernel: Optional[object] = None,
        use_governance_extensions: bool = False,
    ) -> None:
        self._governance_extensions_enabled = use_governance_extensions
        if use_governance_extensions and governance_kernel is not None:
            from constitutional_architecture.governance.audit import AuditEvidenceRecorder
            from constitutional_architecture.governance.integration import GovernedKernel
            from constitutional_architecture.governance.versioning import (
                InMemoryConstitutionVersionRepository,
                VersionManager,
            )

            self._evidence = AuditEvidenceRecorder()
            self._versions = VersionManager(
                InMemoryConstitutionVersionRepository(),
                evidence=self._evidence,
            )
            self.governance_kernel = GovernedKernel(
                governance_kernel,
                evidence=self._evidence,
                versions=self._versions,
            )
        else:
            self._evidence = None
            self._versions = None
            self.governance_kernel = governance_kernel

    def evaluate_plugin_approval(
        self,
        manifest: PluginManifestISR,
    ) -> str:
        if self.governance_kernel is not None:
            return self._evaluate_with_kernel(manifest)

        return self._evaluate_reference(manifest)

    def _evaluate_reference(self, manifest: PluginManifestISR) -> str:
        capabilities = set(manifest.capabilities)

        if capabilities.intersection(self.HIGH_RISK_CAPABILITIES):
            return "REQUIRE_APPROVAL"

        return "ALLOW"

    def _evaluate_with_kernel(self, manifest: PluginManifestISR) -> str:
        """Delegate approval to the Phase 28 Constitutional Governance Kernel."""
        from constitutional_architecture.governance import (
            GovernanceEvaluationRequest,
        )
        from constitutional_architecture.governance.schemas import (
            Actor,
            ActorType,
            Decision,
        )

        actor = Actor(
            actor_type=ActorType.PLUGIN,
            actor_id="marketplace_engine",
            roles=[],
        )

        request = GovernanceEvaluationRequest(
            subject_type="PLUGIN",
            subject_id=manifest.id,
            action="PLUGIN_APPROVAL",
            actor=actor,
            context={
                "plugin_name": manifest.name,
                "version": manifest.version,
                "publisher_id": manifest.publisher_id,
                "capabilities": [c.value for c in manifest.capabilities],
                "dependencies": dict(manifest.dependencies),
            },
            evidence_refs=[],
            requested_exceptions=[],
        )

        decision = self.governance_kernel.evaluate(request)

        if decision.decision in (Decision.ALLOW, Decision.ALLOW_WITH_CONSTRAINTS):
            return "ALLOW"

        # DENY / REQUIRE_APPROVAL / REQUIRE_EVIDENCE -> route to governance review
        return "REQUIRE_APPROVAL"


class PluginEcosystemEngine:
    """Coordinates plugin publishing, installation, execution, and revocation."""

    def __init__(
        self,
        governance: Optional[GovernanceGateway] = None,
    ) -> None:
        self.governance = governance or GovernanceGateway()

        self.publishers: Dict[str, PublisherIdentityISR] = {}
        self.listings: Dict[str, MarketplaceListingISR] = {}
        self.revocations: List[RevocationRecordISR] = []

        self.sandbox_executor = SandboxExecutor()

        self._entrypoints: Dict[str, PluginEntrypoint] = {}

    # ------------------------------------------------------------------
    # Publisher registry
    # ------------------------------------------------------------------

    def register_publisher(
        self,
        publisher: PublisherIdentityISR,
    ) -> PublisherIdentityISR:
        self.publishers[publisher.id] = publisher
        return publisher

    def suspend_publisher(
        self,
        publisher_id: str,
        reason: str,
    ) -> PublisherIdentityISR:
        publisher = self.publishers.get(publisher_id)

        if not publisher:
            raise KeyError(f"Publisher not found: {publisher_id}")

        publisher.status = PublisherStatus.SUSPENDED

        return publisher

    # ------------------------------------------------------------------
    # Plugin code registry
    # ------------------------------------------------------------------

    def register_entrypoint(
        self,
        plugin_id: str,
        entrypoint: PluginEntrypoint,
    ) -> None:
        self._entrypoints[plugin_id] = entrypoint

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------

    def publish_plugin(
        self,
        manifest: PluginManifestISR,
    ) -> MarketplaceListingISR:
        if not verify_manifest_signature(manifest):
            raise ValueError("Invalid manifest signature.")

        publisher = self.publishers.get(manifest.publisher_id)

        if not publisher:
            raise ValueError("Unknown publisher.")

        if publisher.status != PublisherStatus.ACTIVE:
            raise ValueError("Publisher is not active.")

        listing = MarketplaceListingISR(manifest=manifest)

        decision = self.governance.evaluate_plugin_approval(manifest)

        if decision == "REQUIRE_APPROVAL":
            listing.status = PluginStatus.PENDING_REVIEW
            listing.audit_trail.append(
                "Requires governance approval due to high-risk capabilities."
            )
        else:
            listing.status = PluginStatus.APPROVED
            listing.audit_trail.append("Auto-approved by governance policy.")

        self.listings[listing.id] = listing

        return listing

    def approve_plugin(
        self,
        listing_id: str,
        approver_id: str,
    ) -> MarketplaceListingISR:
        listing = self._get_listing(listing_id)

        if listing.status != PluginStatus.PENDING_REVIEW:
            raise ValueError("Plugin is not pending review.")

        listing.status = PluginStatus.APPROVED
        listing.approval_ref = f"governance:{approver_id}"
        listing.audit_trail.append(f"Approved by {approver_id}.")

        return listing

    # ------------------------------------------------------------------
    # Installation
    # ------------------------------------------------------------------

    def install_plugin(
        self,
        listing_id: str,
    ) -> MarketplaceListingISR:
        listing = self._get_listing(listing_id)

        if listing.status != PluginStatus.APPROVED:
            raise ValueError("Plugin must be approved before installation.")

        installed_listings = {
            candidate_id: candidate
            for candidate_id, candidate in self.listings.items()
            if candidate.status == PluginStatus.INSTALLED
        }

        resolver = DependencyResolver(installed_listings)

        report = resolver.validate(listing.manifest)

        if not report.is_compatible:
            listing.status = PluginStatus.QUARANTINED
            listing.audit_trail.append(f"Quarantined: {report.reason}")

            raise ValueError(f"Compatibility check failed: {report.reason}")

        listing.status = PluginStatus.INSTALLED
        listing.installed_at = utcnow()
        listing.audit_trail.append("Installed successfully.")

        return listing

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def execute_plugin(self, listing_id: str) -> Dict:
        listing = self._get_listing(listing_id)

        if listing.status != PluginStatus.INSTALLED:
            raise ValueError("Plugin is not installed.")

        entrypoint = self._entrypoints.get(listing.manifest.id)

        if not entrypoint:
            raise RuntimeError("Plugin entrypoint not registered.")

        context = PluginExecutionContext(
            plugin_id=listing.manifest.id,
            policy=listing.manifest.sandbox_policy,
        )

        try:
            result = self.sandbox_executor.execute(entrypoint, context)

        except SandboxViolation:
            listing.status = PluginStatus.QUARANTINED
            listing.audit_trail.append(
                "QUARANTINED: plugin violated its sandbox policy."
            )
            raise

        listing.audit_trail.append("Executed successfully inside sandbox.")

        return {
            "status": "success",
            "result": result,
            "network_calls": context.network_calls,
            "isr_mutations": context.isr_mutations,
            "file_reads": context.file_reads,
            "file_writes": context.file_writes,
        }

    # ------------------------------------------------------------------
    # Revocation
    # ------------------------------------------------------------------

    def revoke_plugin(
        self,
        listing_id: str,
        reason: str,
        revoked_by: str,
    ) -> RevocationRecordISR:
        listing = self._get_listing(listing_id)

        listing.status = PluginStatus.REVOKED
        listing.revoked_at = utcnow()
        listing.revocation_reason = reason
        listing.audit_trail.append(f"Revoked by {revoked_by}: {reason}")

        affected_dependents: List[str] = []

        for candidate_id, candidate in self.listings.items():
            if candidate_id == listing_id:
                continue

            if candidate.status != PluginStatus.INSTALLED:
                continue

            dependencies = candidate.manifest.dependencies

            if listing.manifest.name in dependencies:
                candidate.status = PluginStatus.QUARANTINED
                candidate.audit_trail.append(
                    "Quarantined because dependency was revoked: "
                    f"{listing.manifest.name}"
                )

                affected_dependents.append(candidate_id)

        record = RevocationRecordISR(
            plugin_id=listing_id,
            plugin_version=listing.manifest.version,
            reason=reason,
            revoked_by=revoked_by,
            affected_dependents=affected_dependents,
        )

        self.revocations.append(record)

        return record

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_listing(self, listing_id: str) -> MarketplaceListingISR:
        return self._get_listing(listing_id)

    def list_listings(self) -> List[MarketplaceListingISR]:
        return list(self.listings.values())

    def list_revocations(self) -> List[RevocationRecordISR]:
        return list(self.revocations)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_listing(self, listing_id: str) -> MarketplaceListingISR:
        listing = self.listings.get(listing_id)

        if not listing:
            raise KeyError(f"Listing not found: {listing_id}")

        return listing
