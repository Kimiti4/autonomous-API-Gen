"""Frontend semantic contract manifest.

The manifest is shared by web, iOS, Android and future desktop/cross-platform
targets. Platform-specific compilers must preserve it.
"""
from __future__ import annotations
from .frontend_ir import FrontendProjectIR


def frontend_contract_manifest(ir: FrontendProjectIR) -> dict:
    return {
        "schema_version": ir.schema_version,
        "application_id": ir.application_id,
        "api_contract_version": ir.api_contract_version,
        "screens": [
            {
                "screen_id": s.screen_id,
                "route": s.route,
                "title": s.title,
                "data_contract": s.data_contract,
                "authorization_policy": s.authorization_policy,
                "actions": sorted(s.actions),
                "accessibility_requirements": sorted(s.accessibility_requirements),
            }
            for s in sorted(ir.screens, key=lambda x: x.screen_id)
        ],
        "platform_requirements": sorted(ir.platform_requirements),
        "configuration_keys": sorted(ir.configuration_keys),
    }
