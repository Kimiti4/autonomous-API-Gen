"""
Phase 28.1 — PEP enforcement decorators (Milestone 5B).

@governed_action gives any subsystem method a Policy Enforcement Point
without touching kernel internals: evaluate -> enforce -> run the guarded
body only on ALLOW / satisfied constraints. Requires the decorated method
(or its instance) to expose the actor and context, or accept them as
keyword arguments.
"""

from __future__ import annotations

import functools
from typing import Any, Callable, Optional

from constitutional_architecture.governance.pep.enforcement import PEPEnforcer


def governed_action(
    *,
    subject_type: str,
    action: str,
    subject_id_arg: Optional[str] = None,
    context_arg: Optional[str] = None,
    evidence_arg: Optional[str] = None,
    environment: str = "staging",
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator enforcing governance before a guarded action runs.

    The wrapped callable receives actor / subject_id / context / evidence
    either from named keyword arguments (context_arg etc.) or from the
    instance attribute `governance_context` (dict with keys actor,
    subject_id, context, evidence_refs). If the instance provides a
    `governance_enforcer` attribute, it is used; otherwise a PEPEnforcer is
    built from the instance's `governance_client` (or `kernel`).
    """

    def decorate(fn: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(fn)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            enforcer = getattr(self, "governance_enforcer", None)
            if enforcer is None:
                client = getattr(
                    self, "governance_client", None
                ) or getattr(self, "kernel", None)
                if client is None:
                    raise RuntimeError(
                        "governed_action requires instance.governance_enforcer, "
                        "instance.governance_client, or instance.kernel"
                    )
                enforcer = PEPEnforcer(client)
                setattr(self, "governance_enforcer", enforcer)

            external = getattr(self, "governance_context", None) or {}

            def arg(name: Optional[str], default: Any) -> Any:
                if name is not None and name in kwargs:
                    return kwargs[name]
                return external.get(name, default)

            actor = arg("actor", None)
            if actor is None:
                raise RuntimeError(
                    "governed_action requires an actor (arg or governance_context)"
                )
            subject_id = arg("subject_id", None)
            if subject_id is None:
                raise RuntimeError(
                    "governed_action requires a subject_id (arg or governance_context)"
                )

            result = enforcer.enforce(
                subject_type=subject_type,
                subject_id=subject_id,
                action=action,
                actor=actor,
                environment=environment,
                context=arg("context", None),
                evidence_refs=arg("evidence_refs", None),
                on_allowed=lambda r: setattr(self, "_last_enforcement", r),
            )
            kwargs["_enforcement"] = result
            return fn(self, *args, **kwargs)

        return wrapper

    return decorate
