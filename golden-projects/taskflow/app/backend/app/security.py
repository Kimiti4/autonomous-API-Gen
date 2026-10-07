import hashlib
import hmac
import os
import secrets
from uuid import uuid4
from datetime import datetime, timedelta, timezone
import jwt

JWT_SECRET = os.getenv("JWT_SECRET", "taskflow-development-secret-change-me")
JWT_ALGORITHM = "HS256"
JWT_MINUTES = int(os.getenv("JWT_MINUTES", "120"))

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 210_000)
    return salt.hex() + ":" + digest.hex()

def verify_password(password: str, encoded: str) -> bool:
    try:
        salt_hex, digest_hex = encoded.split(":", 1)
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), 210_000)
        return hmac.compare_digest(candidate.hex(), digest_hex)
    except (ValueError, TypeError):
        return False

def create_token(user_id: str) -> tuple[str, str]:
    jti = str(uuid4())
    exp = datetime.now(timezone.utc) + timedelta(minutes=JWT_MINUTES)
    return jwt.encode({"sub": user_id, "jti": jti, "exp": exp}, JWT_SECRET, algorithm=JWT_ALGORITHM), jti

def decode_token(token: str) -> tuple[str, str]:
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    user_id = payload.get("sub")
    jti = payload.get("jti")
    if not user_id or not jti:
        raise ValueError("invalid-token-claims")
    return str(user_id), str(jti)