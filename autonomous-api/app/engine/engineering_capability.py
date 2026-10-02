"""Technology-neutral engineering capability contracts.

Capability profiles express *quality obligations*, not preferred frameworks.
They are inherited by every future compiler target (web, mobile, desktop,
service languages, etc.) and therefore keep engineering quality independent
from implementation technology.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal

Capability = Literal["frontend", "backend", "fullstack"]

@dataclass(frozen=True)
class EngineeringCapability:
    capability_id: str
    role: Capability
    obligation_ids: tuple[str, ...]
    exploration_allowed: bool = True
    framework_prescription: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "capability_id": self.capability_id,
            "role": self.role,
            "obligation_ids": list(self.obligation_ids),
            "exploration_allowed": self.exploration_allowed,
            "framework_prescription": self.framework_prescription,
        }

def capability_for(role: Capability) -> EngineeringCapability:
    from .quality_profiles import profile_for
    obligations = tuple(o.obligation_id for o in profile_for(role).obligations)
    return EngineeringCapability(f"CAP-ENGINEERING-{role.upper()}", role, obligations)
