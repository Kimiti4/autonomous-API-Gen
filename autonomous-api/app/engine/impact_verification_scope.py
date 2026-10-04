"""Verification scope expansion from repository impact evidence."""

from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256

from .repository_impact_analysis import ImpactAnalysis

@dataclass(frozen=True)
class ImpactVerificationScope:
    finding_id: str
    source_path: str
    required_paths: tuple[str, ...]
    impact_digest: str
    digest: str

def derive_impact_verification_scope(
    impact: ImpactAnalysis,
    *,
    baseline_paths: tuple[str, ...] = (),
) -> ImpactVerificationScope:
    required=tuple(sorted(set((impact.source_path, *baseline_paths, *(n.path for n in impact.affected)))))
    canonical="|".join(required)
    digest=sha256(f"{impact.finding_id}|{impact.digest}|{canonical}".encode()).hexdigest()
    return ImpactVerificationScope(impact.finding_id,impact.source_path,required,impact.digest,digest)

def require_impact_verification(
    scope: ImpactVerificationScope,
    verified_paths: tuple[str, ...],
) -> None:
    verified=set(verified_paths)
    missing=tuple(path for path in scope.required_paths if path not in verified)
    if missing:
        raise ValueError("missing-impact-verification:" + ",".join(missing))
