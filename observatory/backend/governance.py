"""Governance command boundary: requests, never direct actions.

Authorization is data-driven against the current authority snapshot:
unknown actions, insufficient clearance, and constitutionally blocked
actions all fail closed with reasons. This module executes nothing.
"""
from __future__ import annotations

from typing import Dict, List

from .domain import Actor

READ_ACTIONS: List[str] = [
    "view_dashboard", "view_overview", "view_runtime", "view_evolution",
    "view_evidence", "view_requirement", "view_capability",
    "view_knowledge", "view_governance", "trace", "explain",
]

COMMAND_ACTIONS: List[str] = [
    "request_authorization", "request_evolution_definition",
    "request_implementation", "request_runtime", "request_production_deploy",
    "safe_mode_enable", "safe_mode_disable", "stop_runtime", "restart_runtime",
]


class AuthorizationError(Exception):
    pass


class GovernanceBoundary:
    def authorize(self, action: str, actor: Actor,
                  authority: Dict[str, str]) -> None:
        if action not in READ_ACTIONS and action not in COMMAND_ACTIONS:
            raise AuthorizationError("unsupported_action")
        self._check_actor(action, actor)
        if action in READ_ACTIONS:
            return  # reads carry no authority precondition beyond role
        self._check_authority(action, authority)

    def _check_actor(self, action: str, actor: Actor) -> None:
        role = actor.role or "observer"
        clearance = actor.clearance or role
        if action in READ_ACTIONS:
            if role in {"observer", "operator", "architect", "admin", "system"}:
                return
            raise AuthorizationError("unauthorized")
        if action in COMMAND_ACTIONS:
            if clearance in {"operator", "architect", "admin"}:
                return
            raise AuthorizationError("unauthorized")
        raise AuthorizationError("unsupported_action")

    def _check_authority(self, action: str, authority: Dict[str, str]) -> None:
        if action == "request_authorization":
            if self._authorized(authority.get("governance"), {"granted"}):
                return
            raise AuthorizationError("blocked_by_constitution")
        if action == "request_evolution_definition":
            if self._authorized(authority.get("evolution"),
                                {"granted", "definition_only"}):
                return
            raise AuthorizationError("blocked_by_constitution")
        if action == "request_implementation":
            if self._authorized(authority.get("implementation"), {"granted"}):
                return
            raise AuthorizationError("blocked_by_constitution")
        if action == "request_runtime":
            if self._authorized(authority.get("runtime"), {"granted"}):
                return
            raise AuthorizationError("blocked_by_constitution")
        if action == "request_production_deploy":
            if self._authorized(authority.get("production"), {"granted"}):
                return
            raise AuthorizationError("blocked_by_constitution")
        if action in {"safe_mode_enable", "safe_mode_disable"}:
            if self._authorized(authority.get("governance"), {"granted"}):
                return
            raise AuthorizationError("blocked_by_constitution")
        if action in {"stop_runtime", "restart_runtime"}:
            if self._authorized(authority.get("runtime"), {"granted"}):
                return
            raise AuthorizationError("blocked_by_constitution")
        raise AuthorizationError("unsupported_action")

    def _authorized(self, value: str | None, allowed_values: set[str]) -> bool:
        return value in allowed_values
