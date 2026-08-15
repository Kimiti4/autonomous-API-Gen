"""
Completeness Levels.

Defines the levels of ISR specification completeness.
Backends declare their minimum required level.
Evolution can operate at any level >= L1.
"""

from __future__ import annotations

from enum import IntEnum, unique


@unique
class CompletenessLevel(IntEnum):
    """
    ISR completeness levels.

    L0: Skeleton — system name, module names only
    L1: Structural — modules, entities, relationships
    L2: Behavioural — services, operations, events, workflows
    L3: Policy — security, governance, operational policies
    L4: Infrastructure — deployment, scaling, networking
    L5: Complete — all layers specified
    """

    L0_SKELETON = 0
    L1_STRUCTURAL = 1
    L2_BEHAVIOURAL = 2
    L3_POLICY = 3
    L4_INFRASTRUCTURE = 4
    L5_COMPLETE = 5

    def __str__(self) -> str:
        return self.name

    @property
    def description(self) -> str:
        descriptions = {
            CompletenessLevel.L0_SKELETON: "System name and module names only",
            CompletenessLevel.L1_STRUCTURAL: "Modules, entities, and relationships defined",
            CompletenessLevel.L2_BEHAVIOURAL: "Services, operations, events, and workflows defined",
            CompletenessLevel.L3_POLICY: "Security, governance, and operational policies defined",
            CompletenessLevel.L4_INFRASTRUCTURE: "Deployment, scaling, and networking defined",
            CompletenessLevel.L5_COMPLETE: "All layers fully specified",
        }
        return descriptions[self]

    @property
    def allows_evolution(self) -> bool:
        return self >= CompletenessLevel.L1_STRUCTURAL

    @property
    def allows_compilation(self) -> bool:
        return self >= CompletenessLevel.L2_BEHAVIOURAL
