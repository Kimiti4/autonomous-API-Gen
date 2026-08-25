"""35.1 Failure taxonomy -- canonical registry."""
from __future__ import annotations
from dataclasses import dataclass
from tiannara.domain.services.canonical import canonical_hash
CATEGORIES = {
    "process": ("process_crash","supervisor_restart","crash_loop"),
    "resource": ("memory_exhaustion","disk_exhaustion","connection_pool_exhaustion"),
    "infrastructure": ("database_unavailable","network_partition","dependency_timeout"),
    "distributed": ("duplicate_delivery","stale_read","split_brain","leader_failure"),
    "deployment": ("failed_deployment","rollback_failure"),
    "temporal": ("clock_skew","timeout_cascade","retry_storm"),
}
ALL_FAILURES = tuple(v for vs in CATEGORIES.values() for v in vs)
@dataclass(frozen=True)
class FailureDefinition:
    failure_id: str; category: str; critical: bool
REGISTRY = tuple(FailureDefinition(fid, cat, fid in ("process_crash","split_brain","database_unavailable")) for cat, fids in CATEGORIES.items() for fid in fids)
def content_hash(): return canonical_hash([f.failure_id for f in REGISTRY])
def is_known(fid): return fid in ALL_FAILURES
