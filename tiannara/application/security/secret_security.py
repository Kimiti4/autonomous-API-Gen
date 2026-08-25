"""34.19 Secret leakage -- search surface actually exercised."""
from __future__ import annotations
import re
PATTERNS = [re.compile(r"AKIA[0-9A-Z]{16}"), re.compile(r"-----BEGIN (RSA )?PRIVATE KEY-----"), re.compile(r"password\s*[:=]\s*\S+", re.I)]
def scan_secrets(text: str, surface_exercised: bool) -> tuple[bool, tuple[str,...]]:
    if not surface_exercised: return (False, ())
    found = []
    for pat in PATTERNS:
        found.extend(pat.findall(text))
    return (bool(found), tuple(found))
