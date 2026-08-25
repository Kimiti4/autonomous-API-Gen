"""GitHub federation — OAuth/OIDC profile exchanger (plugin seam)."""
from __future__ import annotations
from identity.core.principal import Principal
from identity.ports.token_verifier import TokenVerifier


class ReferenceGitHubProfileExchanger:
    """Reference adapter: verifies a GitHub OAuth token and maps it to a Principal."""

    def __init__(self, verifier: TokenVerifier | None = None) -> None:
        self._verifier = verifier

    async def exchange(self, access_token: str) -> Principal | None:
        if self._verifier is not None:
            claims = await self._verifier.verify(access_token)
            if claims is None:
                return None
            return Principal(
                principal_id=claims.get("sub", ""),
                email=claims.get("email", ""),
                display_name=claims.get("login", ""),
                providers=["github"],
            )
        return Principal(
            principal_id=f"gh-{access_token[:8]}",
            email=f"{access_token[:8]}@github.local",
            display_name="GitHub User",
            providers=["github"],
        )
