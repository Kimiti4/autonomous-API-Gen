"""CP067-R6-W07-PLAN — planning register contract (no implementation)."""

from __future__ import annotations

import json
from pathlib import Path

PLAN = Path("certification/atlas/esap/cp067_r6_w07_semantic_preservation_plan.json")


def test_semantic_preservation_plan_is_planning_only():
    payload = json.loads(PLAN.read_text(encoding="utf-8"))
    assert payload["planning_artifact_only"] is True
    assert payload["implementation_authorized"] is False
    assert payload["ratification_required"] is True
    assert payload["preserved_statuses"]["w08_matrix_expansion"] is False
    assert payload["cp068_admission"] == "CP068_CONDITIONAL_ISOLATED_TESTING_ONLY"
    gates = {g["id"]: g["satisfied"] for g in payload["authority_gates"]}
    assert gates["G1"] is False
    assert gates["G3"] is True
    assert len(payload["adversarial_cases_required"]) >= 5
