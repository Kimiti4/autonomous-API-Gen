"""GitHub publication adapter placeholder.

This class is intentionally non-operational. It must never return a
production-looking success until a real authenticated GitHub API adapter has
been implemented and independently tested.
"""
from dataclasses import dataclass, field
from typing import Mapping

from tiannara.application.publication.repository_publisher_contract import (
    ProviderPublicationReceipt,
    SystemDeploymentBundle,
)


@dataclass
class GitHubProvider:
    token: str = field(default="", repr=False)

    @staticmethod
    def _not_configured() -> None:
        raise RuntimeError(
            "GitHub publication is not configured: this adapter has no live API implementation"
        )

    def publish_repository(
        self,
        name: str,
        bundle: SystemDeploymentBundle,
        files: Mapping[str, str],
    ) -> ProviderPublicationReceipt:
        self._not_configured()

    def verify_publication(self, receipt, files) -> bool:
        self._not_configured()

    def create_repository(self, name: str, bundle) -> str:
        self._not_configured()

    def push_repository(self, local_path: str, remote_url: str) -> str:
        self._not_configured()

    def create_release(self, repo: str, tag: str) -> str:
        self._not_configured()

    def create_milestone(self, repo: str, title: str) -> str:
        self._not_configured()

    def create_issue(self, repo: str, title: str) -> str:
        self._not_configured()

    def configure_branch_protection(self, repo: str) -> str:
        self._not_configured()

    def configure_security(self, repo: str) -> str:
        self._not_configured()
