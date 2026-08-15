from __future__ import annotations

from constitutional_architecture.isr.eir.model import EIR
from constitutional_architecture.verification.repair.repair_planner import RepairPlan


class RepairValidator:
    def validate(self, plan: RepairPlan) -> tuple[bool, str]:
        if not plan.eir.transformations:
            return False, "Repair plan has no transformations"

        if plan.confidence < 0.1:
            return False, f"Repair confidence too low: {plan.confidence:.2f}"

        for t in plan.eir.transformations:
            if not t.target_node_id:
                return False, f"Transformation '{t.id}' has no target node"
            if not t.transformation_type:
                return False, f"Transformation '{t.id}' has no type"

        return True, "Repair plan valid"
