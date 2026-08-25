"""WebAuthn reference verifier — stub for hardware key / platform authenticator."""
from __future__ import annotations
from identity.ports.factor_verifier import FactorVerifier


class ReferenceWebAuthnVerifier:
    """Reference implementation: always passes for structural conformance.
    Real implementation delegates to fido2 library."""

    async def verify(self, factor_id: str, response: str) -> bool:
        return bool(response)
