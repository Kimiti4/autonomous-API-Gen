"""GitHub Provider -- first provider, no assumptions leak into ISR."""
from dataclasses import dataclass
@dataclass
class GitHubProvider:
    token: str = ""  # must remain outside ISR
    def create_repository(self, name: str, bundle) -> str:
        # Simulated creation - in real would call GitHub API
        return f"https://github.com/kimiti4/{name}"
    def push_repository(self, local_path: str, remote_url: str) -> str:
        return f"pushed to {remote_url}"
    def create_release(self, repo: str, tag: str) -> str:
        return f"release {tag} for {repo}"
    def create_milestone(self, repo: str, title: str) -> str:
        return f"milestone {title}"
    def create_issue(self, repo: str, title: str) -> str:
        return f"issue {title}"
    def configure_branch_protection(self, repo: str) -> str:
        return "branch protection configured"
    def configure_security(self, repo: str) -> str:
        return "security configured"
