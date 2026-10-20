"""Technology-neutral frontend IR with explicit API action bindings."""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any


@dataclass(frozen=True)
class FrontendActionBinding:
    """An explicit UI action → API operation binding; no name-based inference."""
    action_id: str
    api_operation_id: str
    method: str
    path: str
    request_fields: tuple[str, ...] = ()
    authorization_policy: str | None = None


@dataclass(frozen=True)
class FrontendScreen:
    screen_id: str
    route: str
    title: str
    data_contract: str | None = None
    authorization_policy: str | None = None
    actions: tuple[str, ...] = ()
    accessibility_requirements: tuple[str, ...] = ()
    action_bindings: tuple[FrontendActionBinding, ...] = ()


@dataclass(frozen=True)
class FrontendProjectIR:
    schema_version: str
    application_id: str
    screens: tuple[FrontendScreen, ...]
    api_contract_version: str
    platform_requirements: tuple[str, ...] = ()
    configuration_keys: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "application_id": self.application_id,
            "api_contract_version": self.api_contract_version,
            "screens": [
                {
                    "screen_id": screen.screen_id,
                    "route": screen.route,
                    "title": screen.title,
                    "data_contract": screen.data_contract,
                    "authorization_policy": screen.authorization_policy,
                    "actions": list(screen.actions),
                    "accessibility_requirements": list(screen.accessibility_requirements),
                    "action_bindings": [
                        {
                            "action_id": binding.action_id,
                            "api_operation_id": binding.api_operation_id,
                            "method": binding.method,
                            "path": binding.path,
                            "request_fields": list(binding.request_fields),
                            "authorization_policy": binding.authorization_policy,
                        }
                        for binding in screen.action_bindings
                    ],
                }
                for screen in self.screens
            ],
            "platform_requirements": list(self.platform_requirements),
            "configuration_keys": list(self.configuration_keys),
        }


def validate_frontend_ir(ir: FrontendProjectIR) -> tuple[str, ...]:
    findings: list[str] = []
    if not ir.schema_version:
        findings.append("missing schema_version")
    if not ir.application_id:
        findings.append("missing application_id")
    if not ir.api_contract_version:
        findings.append("missing api_contract_version")
    if not ir.screens:
        findings.append("frontend IR has no screens")
    seen: set[str] = set()
    seen_routes: set[str] = set()
    for screen in ir.screens:
        if not screen.screen_id:
            findings.append("screen missing screen_id")
        if screen.screen_id in seen:
            findings.append(f"duplicate screen_id: {screen.screen_id}")
        seen.add(screen.screen_id)
        if screen.route in seen_routes:
            findings.append(f"duplicate screen route: {screen.route}")
        seen_routes.add(screen.route)
        if len(screen.actions) != len(set(screen.actions)):
            findings.append(f"duplicate action ID on screen: {screen.screen_id}")
        if not screen.route.startswith("/"):

            findings.append(f"screen route must start with '/': {screen.screen_id}")
        if not screen.title:
            findings.append(f"screen missing title: {screen.screen_id}")
        binding_ids: set[str] = set()
        for binding in screen.action_bindings:
            if binding.action_id not in screen.actions:
                findings.append(f"action binding references undeclared action: {binding.action_id}")
            if binding.action_id in binding_ids:
                findings.append(f"duplicate action binding: {binding.action_id}")
            binding_ids.add(binding.action_id)
            if not binding.api_operation_id:
                findings.append(f"action binding missing API operation ID: {binding.action_id}")
            if binding.method.upper() not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
                findings.append(f"unsupported API method for action: {binding.action_id}")
            if not binding.path.startswith("/"):
                findings.append(f"action API path must start with '/': {binding.action_id}")
            if len(binding.request_fields) != len(set(binding.request_fields)):
                findings.append(f"duplicate request field in action binding: {binding.action_id}")
            for field in binding.request_fields:
                if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,127}", field):
                    findings.append(f"invalid request field name in action binding: {field}")
    for key in ir.configuration_keys:
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,127}", key):
            findings.append(f"invalid configuration key: {key}")
    return tuple(findings)
