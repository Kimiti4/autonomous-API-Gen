"""GitHub repository publisher via git-over-HTTPS (no PyGithub dependency).

Credentials are passed to git through GIT_ASKPASS so the token never appears in
remote URLs, process arguments, or logs. Network-bound; not exercised by the
unit suite (which uses LocalRepositoryPublisher).
"""
import asyncio
import logging
import os
import subprocess
from ...domain.ports import RepositoryPublisher

logger = logging.getLogger(__name__)


class GitHubRepositoryPublisher:
    API = "https://api.github.com"

    def __init__(self, token: str, default_branch: str = "main") -> None:
        self._token = token
        self._branch = default_branch

    async def publish(self, bundle, evidence, owner, author_name, author_email,
                      repo_name: str | None = None) -> str:
        import httpx
        repo_name = repo_name or evidence.project_id
        async with httpx.AsyncClient(
            base_url=self.API,
            headers={"Authorization": f"Bearer {self._token}",
                     "Accept": "application/vnd.github+json"},
            timeout=30.0,
        ) as client:
            await self._ensure_repository_exists(client, owner, repo_name)
        await self._git_push(bundle.path, owner, repo_name, author_name, author_email)
        return f"https://github.com/{owner}/{repo_name}"

    async def _ensure_repository_exists(self, client, owner: str, repo: str) -> None:
        try:
            resp = await client.get(f"/repos/{owner}/{repo}")
            resp.raise_for_status()
            return
        except Exception:
            resp = await client.post(f"/repos/{owner}", json={"name": repo, "private": True})
            resp.raise_for_status()

    async def _git_push(self, directory, owner, repo, author_name, author_email) -> None:
        env = dict(os.environ)
        askpass = directory.parent / ".git-askpass.sh"
        askpass.write_text(f"#!/bin/sh\necho '{self._token}'\n")
        os.chmod(askpass, 0o700)
        env["GIT_ASKPASS"] = str(askpass)
        env["GIT_TERMINAL_PROMPT"] = "0"
        await asyncio.to_thread(
            self._run, ["git", "init", "-b", self._branch], directory, env)
        await asyncio.to_thread(
            self._run, ["git", "-c", f"user.name={author_name}", "-c", f"user.email={author_email}",
                        "add", "."], directory, env)
        await asyncio.to_thread(
            self._run, ["git", "-c", f"user.name={author_name}", "-c", f"user.email={author_email}",
                        "commit", "-m", f"chore: generated repository {repo} from ISR lineage"],
            directory, env)
        await asyncio.to_thread(
            self._run, ["git", "remote", "add", "origin", f"https://{owner}/{repo}.git"],
            directory, env)
        await asyncio.to_thread(
            self._run, ["git", "push", "-u", "origin", self._branch], directory, env)

    @staticmethod
    def _run(cmd, cwd, env) -> None:
        subprocess.run(cmd, cwd=str(cwd), env=env, check=True)
