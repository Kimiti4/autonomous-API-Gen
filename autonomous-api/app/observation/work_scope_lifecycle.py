"""Governed ESAP work-scope lifecycle projection for the Observatory."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from app.observation.contracts.work_scope import WorkScopeDeclared
from app.observation.mutation_authorization_events import MutationAuthorizationObserved
from app.observation.mutation_execution_events import MutationExecutionObserved
from app.observation.mutation_verification_events import MutationVerificationObserved


@dataclass(frozen=True)
class WorkScopeLifecycle:
    scope: WorkScopeDeclared
    authorizations: tuple[MutationAuthorizationObserved, ...] = ()
    executions: tuple[MutationExecutionObserved, ...] = ()
    verifications: tuple[MutationVerificationObserved, ...] = ()

    @property
    def authorized_count(self) -> int:
        return sum(x.decision == "AUTHORIZED" for x in self.authorizations)

    @property
    def blocked_count(self) -> int:
        return sum(x.decision == "BLOCKED" for x in self.authorizations)

    @property
    def executed_count(self) -> int:
        return sum(x.status == "EXECUTED" for x in self.executions)

    @property
    def failed_execution_count(self) -> int:
        return sum(x.status == "FAILED" for x in self.executions)

    @property
    def aborted_execution_count(self) -> int:
        return sum(x.status == "ABORTED" for x in self.executions)

    @property
    def verified_count(self) -> int:
        return sum(x.status == "VERIFIED" for x in self.verifications)

    @property
    def failed_verification_count(self) -> int:
        return sum(x.status == "FAILED" for x in self.verifications)

    @property
    def admitted_count(self) -> int:
        return sum(x.admission == "ADMITTED" for x in self.verifications)

    @property
    def rejected_count(self) -> int:
        return sum(x.admission == "REJECTED" for x in self.verifications)


def project_work_scope_lifecycle(
    events: Iterable[object],
) -> WorkScopeLifecycle:
    scope = None
    authorizations = []
    executions = []
    verifications = []

    for event in events:
        event_type = getattr(event, "eventType", None)
        payload = getattr(event, "payload", None)
        if event_type == "scope.declared":
            if scope is not None:
                raise ValueError("multiple-work-scope-declarations")
            scope = payload
        elif event_type == "mutation.authorization":
            authorizations.append(payload)
        elif event_type == "mutation.execution":
            executions.append(payload)
        elif event_type == "mutation.verification":
            verifications.append(payload)

    if scope is None:
        raise ValueError("missing-work-scope-declaration")

    return WorkScopeLifecycle(
        scope=scope,
        authorizations=tuple(authorizations),
        executions=tuple(executions),
        verifications=tuple(verifications),
    )
