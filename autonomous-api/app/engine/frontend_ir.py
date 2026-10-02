"""Technology-neutral frontend IR.

The frontend compiler boundary is deliberately separate from React, mobile
toolkits, or native UI frameworks. It models screens, navigation, data
contracts, actions, authorization and accessibility obligations.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FrontendScreen:
    screen_id: str
    route: str
    title: str
    data_contract: str | None = None
    authorization_policy: str | None = None
    actions: tuple[str, ...] = ()
    accessibility_requirements: tuple[str, ...] = ()


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
                    "screen_id": s.screen_id,
                    "route": s.route,
                    "title": s.title,
                    "data_contract": s.data_contract,
                    "authorization_policy": s.authorization_policy,
                    "actions": list(s.actions),
                    "accessibility_requirements": list(s.accessibility_requirements),
                }
                for s in self.screens
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
    seen: set[str] = set()
    for screen in ir.screens:
        if not screen.screen_id:
            findings.append("screen missing screen_id")
        if screen.screen_id in seen:
            findings.append(f"duplicate screen_id: {screen.screen_id}")
        seen.add(screen.screen_id)
        if not screen.route.startswith("/"):
            findings.append(f"screen route must start with '/': {screen.screen_id}")
        if not screen.title:
            findings.append(f"screen missing title: {screen.screen_id}")
    return tuple(findings)
