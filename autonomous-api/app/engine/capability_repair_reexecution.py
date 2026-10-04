"""Capability-aware closure for repaired Bucket 2 work."""

from __future__ import annotations

from .capability_repair_routing import route_capability_failures
from .repair_reexecution import RepairedCandidate, reexecute_repaired_candidate
from .verification_failure_repair import VerificationRepairRequest


def reexecute_capability_repair(
    mode,
    request: VerificationRepairRequest,
    repair_execution,
    *,
    result,
    dependency_graph,
    dependent_specs,
    verifiers,
    observations,
    evidence_by_property,
    successor_architecture_id,
) -> RepairedCandidate:
    route_capability_failures(mode, request.failures)
    if repair_execution is None:
        raise ValueError("missing-capability-repair-execution")
    return reexecute_repaired_candidate(
        result,
        repair_execution,
        dependency_graph=dependency_graph,
        dependent_specs=dependent_specs,
        verifiers=verifiers,
        observations=observations,
        evidence_by_property=evidence_by_property,
        successor_architecture_id=successor_architecture_id,
    )
