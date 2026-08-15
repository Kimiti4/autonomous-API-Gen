"""LocalGitBackend -- real git operations in a local, path-isolated repo.

Git is invoked as a CLI behind the ``SourceControlBackend`` port. Commits use
``-c user.name=`` / ``-c user.email=`` so identity is supplied per call and
never depends on global config (the #1 failure mode for hermetic git tests).

Remote operations (``push``/``create_pull_request``) are not hermetic: they
raise ``SourceControlError`` rather than silently fabricating a result.
"""
from __future__ import annotations

import shutil
import subprocess

from tiannara.domain.ports.source_control import (
    CommitRef,
    PullRequestRef,
    SourceControlError,
)


class LocalGitBackend:
    """Real git backend operating on a local directory."""

    def _run(
        self, repo_root: str, args: list[str], *, check: bool = True
    ) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", "-C", repo_root, *args],
            check=check,
            text=True,
            capture_output=True,
        )

    def ensure_available(self) -> bool:
        return shutil.which("git") is not None

    def init(self, repo_root: str) -> None:
        subprocess.run(["git", "init", repo_root], check=True, text=True, capture_output=True)
        # Pin the default branch to `main` without relying on init.defaultBranch.
        self._run(repo_root, ["symbolic-ref", "HEAD", "refs/heads/main"])

    def add(self, repo_root: str, paths: list[str]) -> None:
        self._run(repo_root, ["add", "--", *paths])

    def commit(
        self, repo_root: str, message: str, author_name: str, author_email: str
    ) -> CommitRef:
        self._run(
            repo_root,
            [
                "-c",
                f"user.name={author_name}",
                "-c",
                f"user.email={author_email}",
                "commit",
                "-m",
                message,
            ],
        )
        head = self._run(
            repo_root, ["rev-parse", "HEAD"], check=True
        ).stdout.strip()
        branch = self._run(
            repo_root, ["rev-parse", "--abbrev-ref", "HEAD"], check=True
        ).stdout.strip()
        return CommitRef(commit_id=head, branch=branch, message=message)

    def branch(self, repo_root: str, name: str) -> None:
        self._run(repo_root, ["branch", "-M", name])

    def push(self, repo_root: str, remote: str, branch: str) -> None:
        try:
            self._run(repo_root, ["push", remote, branch])
        except subprocess.CalledProcessError as exc:
            raise SourceControlError(
                f"git push to {remote}/{branch} failed: {exc.stderr.strip() or exc}"
            ) from exc

    def create_pull_request(
        self, repo_root: str, source_branch: str, target_branch: str, title: str, body: str
    ) -> PullRequestRef:
        raise SourceControlError(
            "create_pull_request is not achievable through the local git CLI; "
            "use a hosting-backend port wired to the provider API"
        )
