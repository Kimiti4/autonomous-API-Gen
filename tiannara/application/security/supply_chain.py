"""34.18 Supply Chain -- integrity, provenance, no arbitrary deps."""
from __future__ import annotations
from dataclasses import dataclass
from tiannara.domain.services.canonical import canonical_hash
@dataclass(frozen=True)
class Dependency: name: str; version: str; hash: str; provenance: str
def verify_integrity(declared: Dependency, lockfile: dict) -> bool:
    return lockfile.get(declared.name) == declared.hash
def is_arbitrary(declared: Dependency, allowed: set[str]) -> bool:
    return declared.name not in allowed
def lockfile_hash(lockfile: dict) -> str: return canonical_hash(lockfile)
