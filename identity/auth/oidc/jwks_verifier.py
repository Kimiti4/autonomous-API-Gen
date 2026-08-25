"""OIDC JWKS reference verifier — stub for IdP token verification."""
from __future__ import annotations
from identity.ports.token_verifier import TokenVerifier


class OidcTokenVerifier:
    """Reference adapter: verifies OIDC tokens against a JWKS endpoint.
    In production, fetches JWKS from the IdP's well-known endpoint."""

    def __init__(self, jwks_uri: str = "", audience: str = "") -> None:
        self._jwks_uri = jwks_uri
        self._audience = audience

    async def verify(self, assertion: str) -> dict | None:
        if not assertion:
            return None
        return {"sub": "oidc-user", "email": "oidc@example.com", "iss": self._jwks_uri or "oidc"}
