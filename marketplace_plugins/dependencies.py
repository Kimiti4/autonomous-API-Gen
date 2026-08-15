"""
Dependency resolution and compatibility validation.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from .models import (
    CompatibilityReportISR,
    MarketplaceListingISR,
    PluginManifestISR,
    PluginStatus,
)


def parse_version(version: str) -> Tuple[int, int, int]:
    """Parse a semantic version string."""
    parts = version.strip().split(".")

    if len(parts) != 3:
        raise ValueError(f"Invalid semantic version: {version}")

    major, minor, patch = parts

    return int(major), int(minor), int(patch)


def compare_versions(left: str, right: str) -> int:
    """
    Compare two semantic versions.

    Returns:
        -1 if left < right
         0 if left == right
         1 if left > right
    """
    left_parsed = parse_version(left)
    right_parsed = parse_version(right)

    if left_parsed < right_parsed:
        return -1

    if left_parsed > right_parsed:
        return 1

    return 0


def satisfies(version: str, constraint: str) -> bool:
    """
    Check whether a version satisfies a constraint.

    Supported constraints:
        *
        latest
        1.2.3
        >=1.2.3
        <=1.2.3
        >1.2.3
        <1.2.3
        ^1.2.3
        ~1.2.3
    """
    constraint = constraint.strip()

    if constraint in {"*", "latest"}:
        return True

    try:
        if constraint.startswith("^"):
            base = constraint[1:]
            version_parsed = parse_version(version)
            base_parsed = parse_version(base)

            return (
                version_parsed[0] == base_parsed[0]
                and compare_versions(version, base) >= 0
            )

        if constraint.startswith("~"):
            base = constraint[1:]
            version_parsed = parse_version(version)
            base_parsed = parse_version(base)

            return (
                version_parsed[0] == base_parsed[0]
                and version_parsed[1] == base_parsed[1]
                and compare_versions(version, base) >= 0
            )

        if constraint.startswith(">="):
            return compare_versions(version, constraint[2:].strip()) >= 0

        if constraint.startswith("<="):
            return compare_versions(version, constraint[2:].strip()) <= 0

        if constraint.startswith(">"):
            return compare_versions(version, constraint[1:].strip()) > 0

        if constraint.startswith("<"):
            return compare_versions(version, constraint[1:].strip()) < 0

        return compare_versions(version, constraint) == 0

    except ValueError:
        return False


class DependencyResolver:
    """Validates plugin dependencies against installed plugins."""

    def __init__(
        self,
        installed_listings: Dict[str, MarketplaceListingISR],
    ) -> None:
        self.installed = installed_listings

    def validate(self, manifest: PluginManifestISR) -> CompatibilityReportISR:
        missing: List[str] = []
        conflicts: List[str] = []

        installed_by_name: Dict[str, List[MarketplaceListingISR]] = {}

        for listing in self.installed.values():
            if listing.status != PluginStatus.INSTALLED:
                continue

            installed_by_name.setdefault(
                listing.manifest.name,
                [],
            ).append(listing)

        for dependency_name, constraint in manifest.dependencies.items():
            candidates = installed_by_name.get(dependency_name, [])

            if not candidates:
                missing.append(f"{dependency_name} ({constraint})")
                continue

            matching = []

            for listing in candidates:
                try:
                    if satisfies(listing.manifest.version, constraint):
                        matching.append(listing)
                except ValueError:
                    conflicts.append(
                        f"{dependency_name}: invalid version "
                        f"{listing.manifest.version}"
                    )

            if not matching:
                found_versions = ", ".join(
                    sorted({listing.manifest.version for listing in candidates})
                )

                conflicts.append(
                    f"{dependency_name} requires {constraint}; "
                    f"found {found_versions}"
                )

        is_compatible = len(missing) == 0 and len(conflicts) == 0

        reason = (
            "Compatible"
            if is_compatible
            else f"Missing: {missing}; Conflicts: {conflicts}"
        )

        return CompatibilityReportISR(
            plugin_id=manifest.id,
            is_compatible=is_compatible,
            missing_dependencies=missing,
            version_conflicts=conflicts,
            capability_conflicts=[],
            reason=reason,
        )
