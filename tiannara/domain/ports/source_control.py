"""SourceControlBackend port.

Dependency-inverted boundary for source-control operations. Git (and later
GitLab, GitHub, Bitbucket, or a filesystem backend) is an *infrastructure
backend*, never core: the RepositoryMaterializer (Phase 17) depends only on
this port. Implementations live in ``tiannara/infrastructure/source_control``;
tests use the in-memory fake bundled there.

Identity (author name / email) is supplied per ``commit`` call and never held
as backend state, so a hermetic, locally-configured git repo never depends on
global user config.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class CommitRef:
    """Backend-native reference to a created commit."""

    commit_id: str  # e.g. a git sha
    branch: str
    message: str


@dataclass(frozen=True)
class PullRequestRef:
    """Reference to a created pull/merge request."""

    pr_id: str
    source_branch: str
    target_branch: str
    url: str | None = None


class SourceControlError(RuntimeError):
    """Raised when a source-control operation cannot complete."""


@runtime_checkable
class SourceControlBackend(Protocol):
    """Minimal source-control surface used by the Phase 17 materializer."""

    def init(self, repo_root: str) -> None:
        """Create an empty repository at ``repo_root`` (idempotent)."""

    def add(self, repo_root: str, paths: list[str]) -> None:
        """Stage the given paths (repo-root relative) for commit."""

    def commit(
        self,
        repo_root: str,
        message: str,
        author_name: str,
        author_email: str,
    ) -> CommitRef:
        """Create a commit with the supplied identity. Returns the commit ref."""

    def branch(self, repo_root: str, name: str) -> None:
        """Ensure the current HEAD points at (or creates) branch ``name``."""

    def push(self, repo_root: str, remote: str, branch: str) -> None:
        """Push ``branch`` to ``remote``. Raises if no remote is configured."""

    def create_pull_request(
        self,
        repo_root: str,
        source_branch: str,
        target_branch: str,
        title: str,
        body: str,
    ) -> PullRequestRef:
        """Open a pull request. Requires a configured remote + credentials."""
