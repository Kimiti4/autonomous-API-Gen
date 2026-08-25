"""Recovery codes — single-use backup codes for MFA recovery."""
from __future__ import annotations
import hashlib
import os


def generate_recovery_codes(count: int = 10) -> list[str]:
    """Generate plaintext recovery codes."""
    return [f"{os.urandom(4).hex()}-{os.urandom(4).hex()}" for _ in range(count)]


def hash_code(code: str) -> str:
    """Hash a recovery code for storage."""
    return hashlib.sha256(code.encode("utf-8")).hexdigest()
