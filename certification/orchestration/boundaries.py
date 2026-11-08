"""Production routing boundaries (Checkpoint 055)."""
from __future__ import annotations

from certification.orchestration.contract import (
    DirectCompileBoundary,
    OrchestrationLifecycleState,
    RequestKind,
)


class DirectCompileClaimsFullStackError(ValueError):
    """Raised when a subordinate compiler path claims governed completion."""


def assert_direct_compile_boundary(boundary: DirectCompileBoundary) -> None:
    if boundary.completes_lifecycle:
        raise DirectCompileClaimsFullStackError(
            "subordinate-compiler-cannot-claim-full-stack-lifecycle"
        )


def assert_governed_request_kind(request_kind: RequestKind) -> None:
    if request_kind is not RequestKind.FULL_STACK_PRODUCT:
        raise ValueError("orchestration-governed-full-stack-required")


def max_claimed_state_for_dev_compile() -> OrchestrationLifecycleState:
    return OrchestrationLifecycleState.ARTIFACTS_GENERATED
