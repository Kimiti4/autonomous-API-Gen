"""Token verifier port — OIDC/JWKS/GitHub assertion verification seam."""
from __future__ import annotations
from typing import Protocol


class TokenVerifier(Protocol):
    """Verify an external identity assertion (OIDC ID token, GitHub OAuth token, etc.)."""
    async def verify(self, assertion: str) -> dict | None: ...
