"""
Versioning — Immutability and Version Management

The ISR is immutable. Mutations do not modify an ISR in place. Every
mutation produces a new version. This provides complete architectural
lineage, perfect reproducibility, branching evolution, time-travel
debugging, mergeable architectural histories, and evolution provenance.
"""

from constitutional_architecture.versioning.version import (
    VersionManager, ISRVersion, VersionDiff, VersionBranch
)

__all__ = [
    "VersionManager", "ISRVersion", "VersionDiff", "VersionBranch",
]