"""TOTP — Time-based One-Time Password (RFC 6238) reference implementation."""
from __future__ import annotations
import hashlib
import hmac
import struct
import time
import base64
import os


def _int_to_bytes(n: int) -> bytes:
    return struct.pack(">Q", n)


def totp_code(secret_b32: str, time_step: int = 30, digits: int = 6) -> str:
    """Generate current TOTP code from a base32-encoded secret."""
    key = base64.b32decode(secret_b32, casefold=True)
    counter = int(time.time()) // time_step
    mac = hmac.new(key, _int_to_bytes(counter), hashlib.sha1).digest()
    offset = mac[-1] & 0x0F
    code_int = struct.unpack(">I", mac[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(code_int % (10 ** digits)).zfill(digits)


def verify_totp(secret_b32: str, code: str, window: int = 1) -> bool:
    """Verify a TOTP code allowing a time window of +/- steps."""
    key = base64.b32decode(secret_b32, casefold=True)
    counter = int(time.time()) // 30
    for offset in range(-window, window + 1):
        mac = hmac.new(key, _int_to_bytes(counter + offset), hashlib.sha1).digest()
        pos = mac[-1] & 0x0F
        code_int = struct.unpack(">I", mac[pos : pos + 4])[0] & 0x7FFFFFFF
        if hmac.compare_digest(str(code_int % 10**6).zfill(6), code):
            return True
    return False


def generate_secret_b32() -> str:
    """Generate a random TOTP secret encoded as base32."""
    return base64.b32encode(os.urandom(20)).decode("ascii")
