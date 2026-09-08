"""VS-D04 — credential safety + session handling (req-credential-safety).

PBKDF2-SHA256 with per-user salts; secrets never stored or returned.
Session tokens via an injectable generator (production: secrets module;
tests: deterministic counter) so behavior tests stay deterministic.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Callable


def hash_password(password: str, salt_hex: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"),
        bytes.fromhex(salt_hex), 100_000).hex()


def new_salt(random_bytes: Callable[[int], bytes] = secrets.token_bytes) -> str:
    return random_bytes(16).hex()


def verify_password(password: str, salt_hex: str, expected_hex: str) -> bool:
    return hmac.compare_digest(hash_password(password, salt_hex), expected_hex)


def production_token_generator() -> Callable[[], str]:
    def generate() -> str:
        return secrets.token_urlsafe(32)
    return generate
