"""Secret boundary checks for ISR, artifacts and publication.

The scanner is heuristic and intentionally reports only file paths and rule
codes; it never returns or logs matched secret values.
"""
from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import Mapping


_TOKEN_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("AWS_ACCESS_KEY", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("GITHUB_TOKEN", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})\b")),
    ("SLACK_TOKEN", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("GOOGLE_API_KEY", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("STRIPE_SECRET", re.compile(r"\b(?:sk|rk)_(?:live|test)_[0-9A-Za-z]{16,}\b")),
    ("PRIVATE_KEY_BLOCK", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("DATABASE_URL_CREDENTIALS", re.compile(
        r"\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis)://[^/\s:@]+:[^/\s@]{8,}@",
        re.IGNORECASE,
    )),
)

_ASSIGNMENT_PATTERN = re.compile(
    r"\b(?:api[_-]?key|client[_-]?secret|access[_-]?token|refresh[_-]?token|"
    r"password|passwd|secret[_-]?key|private[_-]?key)\b\s*[:=]\s*['\"]?"
    r"([A-Za-z0-9/+=._-]{16,})",
    re.IGNORECASE,
)
_PLACEHOLDER_PREFIXES = (
    "your_", "replace_", "placeholder", "example_", "changeme",
    "change_me", "change-this", "not-a-real", "dummy_",
)


def is_credential_in_isr(isr, credential: str) -> bool:
    if not credential:
        return False
    return credential in str(isr)


def is_credential_in_artifact(artifact: dict, credential: str) -> bool:
    if not credential:
        return False
    return credential in str(artifact)


def is_credential_in_commit(commit_msg: str, credential: str) -> bool:
    if not credential:
        return False
    return credential in commit_msg


def _sensitive_credential_path(path: str) -> bool:
    normalized = path.casefold()
    parts = PurePosixPath(normalized).parts
    name = parts[-1] if parts else normalized
    if name == ".env" or (name.startswith(".env.") and not name.endswith(
        (".example", ".sample", ".template")
    )):
        return True
    if any(part in {".ssh", ".aws"} for part in parts):
        if name not in {"config.example", "credentials.example"}:
            return True
    if name in {"id_rsa", "id_ed25519", "id_ecdsa", "credentials"}:
        return True
    if name.endswith((".pem", ".key", ".p12", ".pfx", ".jks")):
        return True
    return False


def scan_artifact_secrets(artifact_files: Mapping[str, str]) -> tuple[str, ...]:
    """Return non-secret finding identifiers for likely credentials."""
    findings: list[str] = []
    for path, content in artifact_files.items():
        if _sensitive_credential_path(path):
            findings.append(f"{path}:SENSITIVE_CREDENTIAL_FILE")
        if not isinstance(content, str):
            findings.append(f"{path}:NON_TEXT_ARTIFACT")
            continue
        for code, pattern in _TOKEN_PATTERNS:
            if pattern.search(content):
                findings.append(f"{path}:{code}")
        for match in _ASSIGNMENT_PATTERN.finditer(content):
            value = match.group(1).casefold()
            if not value.startswith(_PLACEHOLDER_PREFIXES):
                findings.append(f"{path}:CREDENTIAL_ASSIGNMENT")
                break
    return tuple(sorted(set(findings)))
