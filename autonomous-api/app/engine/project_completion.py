"""Governed project continuation and completion for ESAP Bucket 3.7.

Standalone governance layer. It reconstructs completion state from explicit
obligations and evidence, never invents requirements, and never treats
advisory suggestions as work.

The state machine is fail-closed:
UNKNOWN -> IN_PROGRESS -> VERIFIED -> CERTIFIED
A project is COMPLETE only when every authoritative obligation is certified and
no required obligation remains open. Regressions reopen only affected scope.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Iterable, Literal

ObligationKind = Literal["requirement", "defect", "maintenance", "regression", "verification"]
ObligationStatus = Literal["UNKNOWN", "IN_PROGRESS", "VERIFIED", "CERTIFIED", "REOPENED"]
ProjectStatus = Literal["UNKNOWN", "IN_PROGRESS", "VERIFIED", "CERTIFIED", "COMPLETE"]

_ALLOWED_KINDS = {"requirement", "defect", "maintenance", "regression", "verification"}
_ALLOWED_STATUSES = {"UNKNOWN", "IN_PROGRESS", "VERIFIED", "CERTIFIED", "REOPENED"}


@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    statement: str
    authoritative: bool = False

    def __post_init__(self) -> None:
        if not self.evidence_id.strip() or not self.statement.strip():
            raise ValueError("evidence-requires-id-and-statement")


@dataclass(frozen=True)
class Obligation:
    obligation_id: str
    project_id: str
    kind: ObligationKind
    statement: str
    status: ObligationStatus = "UNKNOWN"
    evidence_ids: tuple[str, ...] = ()
    source: str = "governed"
    parent_obligation_id: str | None = None

    def __post_init__(self) -> None:
        if not self.obligation_id.strip() or not self.project_id.strip():
            raise ValueError("obligation-requires-project-and-id")
        if not self.statement.strip():
            raise ValueError("obligation-requires-statement")
        if self.kind not in _ALLOWED_KINDS:
            raise ValueError("invalid-obligation-kind")
        if self.status not in _ALLOWED_STATUSES:
            raise ValueError("invalid-obligation-status")
        if len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise ValueError("duplicate-obligation-evidence")

    @property
    def certified(self) -> bool:
        return self.status == "CERTIFIED"


@dataclass(frozen=True)
class Advisory:
    advisory_id: str
    project_id: str
    statement: str

    def __post_init__(self) -> None:
        if not self.advisory_id.strip() or not self.project_id.strip():
            raise ValueError("advisory-requires-project-and-id")
        if not self.statement.strip():
            raise ValueError("advisory-requires-statement")


@dataclass(frozen=True)
class CompletionState:
    project_id: str
    status: ProjectStatus
    required_obligation_ids: tuple[str, ...]
    remaining_obligation_ids: tuple[str, ...]
    certified_obligation_ids: tuple[str, ...]
    advisory_ids: tuple[str, ...]
    state_digest: str

    @property
    def complete(self) -> bool:
        return self.status == "COMPLETE"


@dataclass(frozen=True)
class MaintenanceReopen:
    obligation: Obligation
    supersedes_obligation_id: str | None


class ProjectCompletionEngine:
    """Deterministic completion/continuation evaluator.

    Bucket 3.7 owns only completion state. It deliberately does not import or
    mutate Bucket 3.6 memory; an adapter can persist these outcomes later.
    """

    def __init__(
        self,
        *,
        project_id: str,
        obligations: Iterable[Obligation] = (),
        evidence: Iterable[Evidence] = (),
        advisories: Iterable[Advisory] = (),
    ) -> None:
        if not project_id.strip():
            raise ValueError("project-id-required")
        self.project_id = project_id
        self._obligations: dict[str, Obligation] = {}
        self._evidence: dict[str, Evidence] = {}
        self._advisories: dict[str, Advisory] = {}

        for item in evidence:
            self.add_evidence(item)
        for item in obligations:
            self.add_obligation(item)
        for item in advisories:
            self.add_advisory(item)

    def add_evidence(self, item: Evidence) -> None:
        if item.evidence_id in self._evidence:
            raise ValueError("duplicate-evidence-id")
        self._evidence[item.evidence_id] = item

    def add_obligation(self, item: Obligation) -> None:
        if item.project_id != self.project_id:
            raise ValueError("obligation-project-mismatch")
        if item.obligation_id in self._obligations:
            raise ValueError("duplicate-obligation-id")
        if item.parent_obligation_id == item.obligation_id:
            raise ValueError("obligation-self-parent")
        self._validate_obligation_evidence(item)
        self._obligations[item.obligation_id] = item

    def add_advisory(self, item: Advisory) -> None:
        if item.project_id != self.project_id:
            raise ValueError("advisory-project-mismatch")
        if item.advisory_id in self._advisories:
            raise ValueError("duplicate-advisory-id")
        self._advisories[item.advisory_id] = item

    def reconstruct(self) -> CompletionState:
        required = tuple(sorted(self._obligations))
        certified = tuple(sorted(k for k, v in self._obligations.items() if v.certified))
        remaining = tuple(sorted(k for k, v in self._obligations.items() if not v.certified))

        if not required:
            status: ProjectStatus = "UNKNOWN"
        elif remaining:
            status = "IN_PROGRESS"
        else:
            status = "COMPLETE"

        payload = {
            "schema_version": "esap.project-completion.v1",
            "project_id": self.project_id,
            "status": status,
            "required": required,
            "remaining": remaining,
            "certified": certified,
            "advisories": tuple(sorted(self._advisories)),
        }
        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        return CompletionState(
            project_id=self.project_id,
            status=status,
            required_obligation_ids=required,
            remaining_obligation_ids=remaining,
            certified_obligation_ids=certified,
            advisory_ids=tuple(sorted(self._advisories)),
            state_digest=digest,
        )

    def certify(self, obligation_id: str, evidence_ids: Iterable[str]) -> Obligation:
        item = self._require(obligation_id)
        ids = tuple(sorted(set(evidence_ids)))
        if not ids:
            raise ValueError("certification-requires-evidence")
        for evidence_id in ids:
            evidence = self._evidence.get(evidence_id)
            if evidence is None:
                raise ValueError("unknown-certification-evidence")
            if not evidence.authoritative:
                raise ValueError("certification-requires-authoritative-evidence")
        updated = Obligation(
            obligation_id=item.obligation_id,
            project_id=item.project_id,
            kind=item.kind,
            statement=item.statement,
            status="CERTIFIED",
            evidence_ids=ids,
            source=item.source,
            parent_obligation_id=item.parent_obligation_id,
        )
        self._obligations[obligation_id] = updated
        return updated

    def mark_verified(self, obligation_id: str, evidence_ids: Iterable[str]) -> Obligation:
        item = self._require(obligation_id)
        ids = tuple(sorted(set(evidence_ids)))
        if not ids:
            raise ValueError("verification-requires-evidence")
        if any(evidence_id not in self._evidence for evidence_id in ids):
            raise ValueError("unknown-verification-evidence")
        updated = Obligation(
            obligation_id=item.obligation_id,
            project_id=item.project_id,
            kind=item.kind,
            statement=item.statement,
            status="VERIFIED",
            evidence_ids=ids,
            source=item.source,
            parent_obligation_id=item.parent_obligation_id,
        )
        self._obligations[obligation_id] = updated
        return updated

    def reopen_for_regression(self, obligation_id: str, regression_statement: str) -> Obligation:
        self._require(obligation_id)
        if not regression_statement.strip():
            raise ValueError("regression-statement-required")
        regression_id = self._stable_id("regression", obligation_id, regression_statement)
        regression = Obligation(
            obligation_id=regression_id,
            project_id=self.project_id,
            kind="regression",
            statement=regression_statement,
            status="REOPENED",
            source="regression",
            parent_obligation_id=obligation_id,
        )
        self._obligations[regression_id] = regression
        return regression

    def request_maintenance(self, statement: str) -> MaintenanceReopen:
        if not statement.strip():
            raise ValueError("maintenance-statement-required")
        parent = self.reconstruct().state_digest
        obligation_id = self._stable_id("maintenance", parent, statement)
        item = Obligation(
            obligation_id=obligation_id,
            project_id=self.project_id,
            kind="maintenance",
            statement=statement,
            status="UNKNOWN",
            source="maintenance-request",
        )
        self._obligations[obligation_id] = item
        return MaintenanceReopen(obligation=item, supersedes_obligation_id=None)

    def reject_unjustified_work(self, statement: str) -> None:
        if not statement.strip():
            raise ValueError("work-statement-required")
        raise ValueError("ungoverned-work-rejected")

    def remaining_work(self) -> tuple[Obligation, ...]:
        return tuple(
            self._obligations[k]
            for k in sorted(self._obligations)
            if not self._obligations[k].certified
        )

    def is_stopped(self) -> bool:
        return self.reconstruct().status == "COMPLETE"

    def _require(self, obligation_id: str) -> Obligation:
        try:
            return self._obligations[obligation_id]
        except KeyError as exc:
            raise ValueError("unknown-obligation-id") from exc

    def _validate_obligation_evidence(self, item: Obligation) -> None:
        for evidence_id in item.evidence_ids:
            if evidence_id not in self._evidence:
                raise ValueError("unknown-obligation-evidence")
        if item.status == "CERTIFIED":
            if not item.evidence_ids:
                raise ValueError("certified-obligation-requires-evidence")
            if not all(self._evidence[e].authoritative for e in item.evidence_ids):
                raise ValueError("certified-obligation-requires-authoritative-evidence")
        if item.status == "REOPENED" and item.kind not in {"regression", "maintenance"}:
            raise ValueError("only-regression-or-maintenance-may-reopen")

    @staticmethod
    def _stable_id(*parts: str) -> str:
        payload = json.dumps(parts, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20]
