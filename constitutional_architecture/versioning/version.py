"""
Versioning — Immutable ISR Version Management

Every ISR mutation produces a new version. This is analogous to Git
commits, except the artifact is architecture rather than source code.

Provides:
- Complete architectural lineage
- Perfect reproducibility
- Branching evolution
- Time-travel debugging
- Mergeable architectural histories
- Evolution provenance
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any, Tuple
from datetime import datetime
from enum import Enum


class VersionStatus(Enum):
    """Status of an ISR version."""
    DRAFT = "draft"
    VALIDATED = "validated"
    COMPILED = "compiled"
    DEPLOYED = "deployed"
    SUPERSEDED = "superseded"
    FAILED = "failed"


@dataclass(frozen=True)
class ISRVersion:
    """A single immutable version of an ISR.

    Each version is identified by its content hash and linked to its
    parent version(s) for full lineage tracking.
    """
    version_number: int
    content_hash: str
    parent_hash: Optional[str] = None
    parent_hashes: List[str] = field(default_factory=list)  # For merges (crossover)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    status: VersionStatus = VersionStatus.DRAFT
    mutation_description: str = ""
    proposed_by: str = "unknown"  # Agent name
    fitness_scores: Dict[str, float] = field(default_factory=dict)
    validation_passed: bool = False
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_ancestor_of(self, other: ISRVersion) -> bool:
        """Check if this version is an ancestor of another."""
        return self.content_hash in other.parent_hashes or (
            other.parent_hash == self.content_hash
        )


@dataclass(frozen=True)
class VersionBranch:
    """A branch of architectural evolution."""
    name: str
    head_hash: str
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    description: str = ""
    version_count: int = 1


@dataclass(frozen=True)
class VersionDiff:
    """A semantic diff between two ISR versions."""
    from_hash: str
    to_hash: str
    added_node_ids: List[str] = field(default_factory=list)
    removed_node_ids: List[str] = field(default_factory=list)
    modified_node_ids: List[str] = field(default_factory=list)
    added_edges: List[Tuple[str, str, str]] = field(default_factory=list)  # (source, target, type)
    removed_edges: List[Tuple[str, str, str]] = field(default_factory=list)
    fitness_delta: Dict[str, float] = field(default_factory=dict)
    summary: str = ""


class VersionManager:
    """Manages immutable ISR versions with full lineage tracking.

    This is the Git for architecture. Every mutation produces a new
    version. The complete evolutionary tree is persisted and
    reconstructable.
    """

    def __init__(self):
        self._versions: Dict[str, ISRVersion] = {}
        self._branches: Dict[str, VersionBranch] = {}
        self._head_hash: Optional[str] = None

    def register_version(self, version: ISRVersion) -> str:
        """Register a new ISR version and return its content hash."""
        self._versions[version.content_hash] = version
        self._head_hash = version.content_hash
        return version.content_hash

    def create_version(
        self,
        content_hash: str,
        parent_hash: Optional[str] = None,
        mutation_description: str = "",
        proposed_by: str = "unknown",
        fitness_scores: Optional[Dict[str, float]] = None,
        tags: Optional[List[str]] = None,
    ) -> ISRVersion:
        """Create and register a new ISR version."""
        parent = self._versions.get(parent_hash) if parent_hash else None
        version_number = (parent.version_number + 1) if parent else 1

        version = ISRVersion(
            version_number=version_number,
            content_hash=content_hash,
            parent_hash=parent_hash,
            parent_hashes=[parent_hash] if parent_hash else [],
            mutation_description=mutation_description,
            proposed_by=proposed_by,
            fitness_scores=fitness_scores or {},
            tags=tags or [],
        )
        return self.register_version(version)

    def create_merged_version(
        self,
        content_hash: str,
        parent_hashes: List[str],
        mutation_description: str = "",
        proposed_by: str = "crossover",
        fitness_scores: Optional[Dict[str, float]] = None,
    ) -> ISRVersion:
        """Create a version that merges multiple parents (crossover)."""
        parents = [h for h in parent_hashes if h in self._versions]
        max_version = max(
            (self._versions[h].version_number for h in parents),
            default=0
        )

        version = ISRVersion(
            version_number=max_version + 1,
            content_hash=content_hash,
            parent_hashes=parent_hashes,
            mutation_description=mutation_description,
            proposed_by=proposed_by,
            fitness_scores=fitness_scores or {},
        )
        return self.register_version(version)

    def get_version(self, content_hash: str) -> Optional[ISRVersion]:
        """Get a version by its content hash."""
        return self._versions.get(content_hash)

    @property
    def head(self) -> Optional[ISRVersion]:
        """Get the current head version."""
        if self._head_hash:
            return self._versions.get(self._head_hash)
        return None

    @property
    def all_versions(self) -> List[ISRVersion]:
        """Get all registered versions, sorted by version number."""
        return sorted(self._versions.values(), key=lambda v: v.version_number)

    def get_lineage(self, content_hash: str) -> List[ISRVersion]:
        """Get the full lineage from a version back to the root."""
        lineage = []
        current = self._versions.get(content_hash)
        while current:
            lineage.append(current)
            if current.parent_hash:
                current = self._versions.get(current.parent_hash)
            else:
                break
        return lineage

    def compute_diff(self, from_hash: str, to_hash: str) -> VersionDiff:
        """Compute a semantic diff between two versions.

        Note: This requires comparing two ISR graph instances.
        The diff is a best-effort comparison based on the metadata
        and changes recorded in the versions.
        """
        from_ver = self._versions.get(from_hash)
        to_ver = self._versions.get(to_hash)

        if not from_ver or not to_ver:
            return VersionDiff(from_hash=from_hash, to_hash=to_hash,
                             summary="One or both versions not found")

        # Compute fitness deltas
        fitness_delta = {}
        all_metrics = set(from_ver.fitness_scores.keys()) | set(to_ver.fitness_scores.keys())
        for metric in all_metrics:
            from_val = from_ver.fitness_scores.get(metric, 0.0)
            to_val = to_ver.fitness_scores.get(metric, 0.0)
            delta = to_val - from_val
            if abs(delta) > 0.001:
                fitness_delta[metric] = round(delta, 4)

        return VersionDiff(
            from_hash=from_hash,
            to_hash=to_hash,
            fitness_delta=fitness_delta,
            summary=f"Version {from_ver.version_number} → {to_ver.version_number}: "
                    f"{to_ver.mutation_description}",
        )

    def create_branch(self, name: str, from_hash: Optional[str] = None,
                      description: str = "") -> VersionBranch:
        """Create a new branch from a given version (or head)."""
        base_hash = from_hash or self._head_hash
        if not base_hash:
            raise ValueError("Cannot create branch: no versions exist")

        branch = VersionBranch(
            name=name,
            head_hash=base_hash,
            description=description,
        )
        self._branches[name] = branch
        return branch

    def get_branch(self, name: str) -> Optional[VersionBranch]:
        """Get a branch by name."""
        return self._branches.get(name)

    def get_lineage_graph(self) -> Dict[str, List[str]]:
        """Get the complete lineage as an adjacency list.

        Useful for visualization and analysis of the evolution tree.
        """
        graph: Dict[str, List[str]] = {}
        for version in self._versions.values():
            children = []
            for other in self._versions.values():
                if version.content_hash in other.parent_hashes:
                    children.append(other.content_hash)
            graph[version.content_hash] = children
        return graph

    def get_evolution_branches(self) -> List[List[ISRVersion]]:
        """Identify distinct evolutionary branches in the version tree."""
        # Find all root versions (no parents)
        roots = [v for v in self._versions.values() if not v.parent_hash
                 and not v.parent_hashes]

        # BFS from each root to find branches
        branches = []
        visited: Set[str] = set()

        for root in roots:
            branch = []
            stack = [root.content_hash]
            while stack:
                current_hash = stack.pop()
                if current_hash in visited:
                    continue
                visited.add(current_hash)
                current = self._versions.get(current_hash)
                if current:
                    branch.append(current)
                    # Find children
                    for other in self._versions.values():
                        if current_hash in other.parent_hashes and \
                           other.parent_hash == current_hash:
                            stack.append(other.content_hash)
            if branch:
                branches.append(branch)

        return branches