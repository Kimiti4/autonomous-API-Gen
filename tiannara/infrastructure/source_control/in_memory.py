"""In-memory SourceControlBackend -- hermetic fake for unit tests."""
from __future__ import annotations

from dataclasses import dataclass, field

from tiannara.domain.ports.source_control import (
    CommitRef,
    PullRequestRef,
    SourceControlError,
)


@dataclass
class _Repo:
    files: set[str] = field(default_factory=set)
    commits: list[CommitRef] = field(default_factory=list)
    branch: str = "main"


@dataclass
class InMemorySourceControlBackend:
    """Records call sequence and simulates enough state for commit refs."""

    repos: dict[str, _Repo] = field(default_factory=dict)
    calls: list[tuple[str, dict]] = field(default_factory=list)

    def init(self, repo_root: str) -> None:
        self.calls.append(("init", {"repo_root": repo_root}))
        self.repos.setdefault(repo_root, _Repo())

    def add(self, repo_root: str, paths: list[str]) -> None:
        self.calls.append(("add", {"repo_root": repo_root, "paths": list(paths)}))
        self.repos[repo_root].files.update(paths)

    def commit(
        self, repo_root: str, message: str, author_name: str, author_email: str
    ) -> CommitRef:
        self.calls.append(
            (
                "commit",
                {
                    "repo_root": repo_root,
                    "message": message,
                    "author_name": author_name,
                    "author_email": author_email,
                },
            )
        )
        repo = self.repos[repo_root]
        ref = CommitRef(
            commit_id=f"sha-{len(repo.commits):04x}",
            branch=repo.branch,
            message=message,
        )
        repo.commits.append(ref)
        return ref

    def branch(self, repo_root: str, name: str) -> None:
        self.calls.append(("branch", {"repo_root": repo_root, "name": name}))
        self.repos[repo_root].branch = name

    def push(self, repo_root: str, remote: str, branch: str) -> None:
        self.calls.append(
            ("push", {"repo_root": repo_root, "remote": remote, "branch": branch})
        )
        raise SourceControlError("no remote configured for in-memory backend")

    def create_pull_request(
        self, repo_root: str, source_branch: str, target_branch: str, title: str, body: str
    ) -> PullRequestRef:
        self.calls.append(
            (
                "create_pull_request",
                {
                    "repo_root": repo_root,
                    "source_branch": source_branch,
                    "target_branch": target_branch,
                    "title": title,
                    "body": body,
                },
            )
        )
        return PullRequestRef(
            pr_id="pr-0001",
            source_branch=source_branch,
            target_branch=target_branch,
            url=None,
        )
