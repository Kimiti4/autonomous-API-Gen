"""Bridge capability-aware repair routing into the existing repair engine."""

from __future__ import annotations

from dataclasses import replace
from typing import Mapping, Any

from .capability_repair_routing import route_capability_failures
from .repair_engine_bridge import EngineRepairResult, execute_verification_repair
from .verification_failure_repair import VerificationRepairRequest


def execute_capability_repair(
    mode,
    request: VerificationRepairRequest,
    *,
    genome,
    repair_specs: Mapping[str, Any],
    observations: Mapping[str, Any],
    contracts_by_domain: Mapping[str, tuple[Any, ...]] | None,
    verifiers: Mapping[str, Any],
    evidence_by_property: Mapping[str, tuple[str, ...]],
) -> EngineRepairResult:
    route = route_capability_failures(mode, request.failures)
    # Require the selected repair candidate to target the same capability route.
    candidate = request.candidate
    if candidate is None:
        raise ValueError("missing-verification-repair-mutation")
    if candidate.domain != route.capability and candidate.domain != route.capability.replace("-", "_"):
        raise ValueError(f"repair-domain-mismatch:{route.capability}:{candidate.domain}")
    return execute_verification_repair(
        request,
        genome=genome,
        repair_specs=repair_specs,
        observations=observations,
        contracts_by_domain=contracts_by_domain,
        verifiers=verifiers,
        evidence_by_property=evidence_by_property,
    )
