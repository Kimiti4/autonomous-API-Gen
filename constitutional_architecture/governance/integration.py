"""Phase 28 - Opt-in integration seam for the existing GovernanceKernel.

GovernedKernel is a composition wrapper (not a subclass): it preserves the
wrapped kernel's PDP/PAP/PEP contract exactly while adding
  1. tamper-evident evidence recording for every decision, and
  2. a fail-closed amendment-authorization check the gateway can consult.

The wrapper never fabricates decisions. For non-amendment requests the
returned decision is byte-identical to the wrapped kernel's, which keeps
`test_governance_kernel_delegates_approval` green without modification.

NOTE: the evidence recorder is injected (never constructed here) so the
composition root can choose signed vs. unsigned ledgering via
``new_evidence_recorder`` (governance.evidence_signing) without the kernel
knowing whether signing is active.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from typing import Any

from .audit import EvidenceLedger
from .versioning import VersionManager


def _safe_dump(value: Any) -> Any:
    """Best-effort canonical dump that is robust to unknown request/decision
    types (pydantic model, dataclass, dict, or arbitrary object)."""
    dump = getattr(value, "model_dump", None)
    if callable(dump):
        return dump()
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    if isinstance(value, dict):
        return value
    return repr(value)


class GovernedKernel:
    """Delegating wrapper: evidence-recording + amendment authorization."""

    def __init__(
        self,
        kernel: Any,
        evidence: EvidenceLedger,
        versions: VersionManager | None = None,
    ) -> None:
        self._kernel = kernel
        self._evidence = evidence
        self._versions = versions

    def evaluate(self, request: Any) -> Any:
        decision = self._kernel.evaluate(request)
        self._evidence.record(
            actor="governance_kernel",
            event_kind="decision",
            subject_ref=str(getattr(request, "request_id", None) or type(request).__name__),
            payload={"request": _safe_dump(request), "decision": _safe_dump(decision)},
            recorded_at=datetime.now(timezone.utc),
        )
        return decision

    def amendment_authorized(self, request: Any) -> bool:
        """Fail-closed authorization for constitutional change requests.

        True only when a ratified head exists AND the request explicitly
        references it via context['ratified_version_ref'].
        """
        if self._versions is None:
            return False
        head = self._versions.current()
        if head is None:
            return False
        context = getattr(request, "context", None) or {}
        return context.get("ratified_version_ref") == head.version_id


# ---------------------------------------------------------------------------
# Wiring sketch for marketplace_plugins/engine.py (ADDITIVE, opt-in):
#
#   from constitutional_architecture.governance.integration import GovernedKernel
#   from constitutional_architecture.governance.evidence_signing import (
#       new_evidence_recorder,
#   )
#
#   # in GovernanceGateway, after the existing kernel delegate is resolved:
#   if self._kernel is not None and governance_extensions_enabled(config):
#       evidence = new_evidence_recorder()  # config-gated: signed if
#                                            # AUDIT_EVIDENCE_SIGNING_KEY is set,
#                                            # unsigned (with a warning) otherwise
#       self._kernel = GovernedKernel(self._kernel, evidence=evidence,
#                                    versions=version_manager)
#
# No change to GovernanceGateway._evaluate_with_kernel is required: it keeps
# calling kernel.evaluate(...) through the same delegate path.
# ---------------------------------------------------------------------------
