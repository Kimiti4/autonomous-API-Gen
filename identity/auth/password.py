"""Password hashing — PBKDF2-SHA256 with per-user salt."""
from __future__ import annotations
import hashlib
import os


class PBKDF2PasswordHasher:
    ITERATIONS = 260_000
    SALT_BYTES = 32
    HASH_BYTES = 32

    def hash(self, password: str) -> str:
        salt = os.urandom(self.SALT_BYTES)
        dk = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, self.ITERATIONS, dklen=self.HASH_BYTES
        )
        return f"{salt.hex()}${dk.hex()}"

    def verify(self, password: str, stored: str) -> bool:
        try:
            salt_hex, hash_hex = stored.split("$", 1)
            salt = bytes.fromhex(salt_hex)
            dk = hashlib.pbkdf2_hmac(
                "sha256", password.encode("utf-8"), salt, self.ITERATIONS, dklen=self.HASH_BYTES
            )
            return dk.hex() == hash_hex
        except Exception:
            return False
