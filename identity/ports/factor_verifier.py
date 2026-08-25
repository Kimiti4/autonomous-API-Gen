"""Factor verifier port — MFA factor verification seam (TOTP, WebAuthn, etc.)."""
from __future__ import annotations
from typing import Protocol


class FactorVerifier(Protocol):
    """Verify an MFA factor challenge response."""
    async def verify(self, factor_id: str, response: str) -> bool: ...
