"""Capability-driven pipeline planning.

Meta-compilers translate StageRequirements into their own stage syntax
(CI YAML, task graphs, ...). They never branch on backend ids. Planning
is a pure function of the manifest: same manifest, same plan, every time.
"""

from __future__ import annotations

from dataclasses import dataclass

from tiannara.domain.models.capability_manifest import (
    BundleCapability,
    CapabilityManifest,
)


@dataclass(frozen=True)
class StageRequirement:
    capability: BundleCapability
    description: str
    ordering_hint: int   # lower runs earlier


#: Canonical plan order. Meta-compilers may refine within a stage but must
#: not reorder across dependency direction (build before test before deploy).
_STAGE_PLAN: tuple[tuple[BundleCapability, str], ...] = (
    (BundleCapability.BUILD, "Compile/assemble produced artifacts"),
    (BundleCapability.LINT, "Run style and consistency checks"),
    (BundleCapability.STATIC_ANALYSIS, "Run deep static analysis"),
    (BundleCapability.SECURITY_SCAN, "Run automated security scans"),
    (BundleCapability.TEST, "Execute the verification suite"),
    (BundleCapability.DATABASE_MIGRATION, "Prepare/apply schema migrations"),
    (BundleCapability.CONTAINERIZE, "Build container images"),
    (BundleCapability.INFRASTRUCTURE_PROVISION, "Provision infrastructure"),
    (BundleCapability.OBSERVABILITY, "Wire observability surfaces"),
    (BundleCapability.HEALTH_CHECK, "Verify liveness/readiness"),
    (BundleCapability.DEPLOY, "Deploy the release unit"),
    (BundleCapability.RELEASE, "Publish release metadata"),
    (BundleCapability.DOCUMENTATION, "Publish generated documentation"),
)


def plan_stages(manifest: CapabilityManifest) -> list[StageRequirement]:
    """Deterministic stage plan derived purely from declared capabilities."""
    return [
        StageRequirement(
            capability=capability, description=description, ordering_hint=index
        )
        for index, (capability, description) in enumerate(_STAGE_PLAN)
        if manifest.provides(capability)
    ]
