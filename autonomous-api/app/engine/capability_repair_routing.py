"""Capability-aware verification failure to repair routing."""

from __future__ import annotations

from dataclasses import dataclass

from .capability_verification import verification_profile
from .verification_failure_repair import VerificationFailure, VerificationRepairRequest


@dataclass(frozen=True)
class CapabilityRepairRoute:
    capability: str
    failed_properties: tuple[str, ...]
    rationale: str


def route_capability_failures(mode, failures: tuple[VerificationFailure, ...]) -> CapabilityRepairRoute:
    profile = verification_profile(mode)
    allowed = set(profile.required_properties)
    failed = tuple(sorted({f.kind for f in failures if f.kind in allowed}))
    if not failed:
        raise ValueError(f"no-capability-failure-to-route:{mode.value}")
    return CapabilityRepairRoute(
        capability=mode.value,
        failed_properties=failed,
        rationale="capability-specific repair required: " + ", ".join(failed),
    )


def attach_capability_route(
    mode, request: VerificationRepairRequest
) -> tuple[VerificationRepairRequest, CapabilityRepairRoute]:
    route = route_capability_failures(mode, request.failures)
    return request, route
