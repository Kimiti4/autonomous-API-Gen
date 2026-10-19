"""Capability gate tests: unsupported semantics must never reach emitters."""
from __future__ import annotations

import pytest

from compiler.backends.python_fastapi import PythonFastAPIBackend
from compiler.backends.rust_axum import RustAxumBackend
from compiler.core.capabilities import (
    BackendCapabilities,
    SemanticFeature,
    UnsupportedSemanticsError,
    assert_plan_supported,
    required_features,
)
from compiler.core.plan import ApiOperation, CompilationPlan, DataModel, Effect
from isr.core.behavior import ApiBehavior, DataModelBehavior, EffectBehavior


def test_structural_plan_requires_no_behavioral_features():
    plan = CompilationPlan(plan_id="plan:1", isr_id="system:1")
    assert required_features(plan) == frozenset()
    assert_plan_supported(plan, BackendCapabilities(backend_id="test", version="1"))


def test_typed_fields_are_detected_as_a_required_capability():
    plan = CompilationPlan(
        plan_id="plan:2",
        isr_id="system:2",
        data_models=[DataModel(
            id="dm:employee",
            entity_name="Employee",
            behavior=DataModelBehavior.model_validate({
                "fields": [{"name": "salary", "value_type": "money", "precision": 12, "scale": 2, "constraints": [{"operator": "unique"}]}]
            }),
        )],
    )
    assert SemanticFeature.TYPED_FIELDS in required_features(plan)
    assert SemanticFeature.FIELD_CONSTRAINTS in required_features(plan)
    with pytest.raises(UnsupportedSemanticsError, match="field_constraints"):
        assert_plan_supported(plan, BackendCapabilities(backend_id="test", version="1"))


@pytest.mark.parametrize("backend", [PythonFastAPIBackend(), RustAxumBackend()])
def test_real_backend_compile_fails_closed_for_unimplemented_semantics(backend):
    plan = CompilationPlan(
        plan_id="plan:3",
        isr_id="system:3",
        data_models=[DataModel(
            id="dm:employee",
            entity_name="Employee",
            behavior=DataModelBehavior.model_validate({
                "fields": [{"name": "salary", "value_type": "money", "precision": 12, "scale": 2}]
            }),
        )],
    )
    with pytest.raises(UnsupportedSemanticsError, match="field_constraints"):
        backend.compile(plan)


def test_supported_behavioral_subset_is_emitted_by_both_backends():
    from compiler.core.plan import Service
    from isr.core.behavior import ServiceBehavior

    model = DataModel(
        id="dm:employee",
        entity_name="Employee",
        behavior=DataModelBehavior.model_validate({
            "fields": [{"name": "base_salary", "value_type": "money", "precision": 12, "scale": 2}]
        }),
    )
    service = Service(
        id="service:payroll",
        name="Payroll",
        data_models=[model],
        behavior=ServiceBehavior.model_validate({
            "rules": [{
                "rule_id": "gross-pay",
                "description": "Gross pay is base salary multiplied by one.",
                "expression": {"op": "multiply", "args": [
                    {"op": "field", "field_ref": "Employee.base_salary"},
                    {"op": "literal", "value": 1},
                ]},
            }],
            "transitions": [{
                "transition_id": "submit",
                "source_state": "draft",
                "target_state": "submitted",
            }],
        }),
    )
    plan = CompilationPlan(plan_id="plan:4", isr_id="system:4", services=[service], data_models=[model])
    assert SemanticFeature.BUSINESS_RULES in required_features(plan)
    assert SemanticFeature.STATE_TRANSITIONS in required_features(plan)
    for backend in (PythonFastAPIBackend(), RustAxumBackend()):
        repo = backend.compile(plan)
        assert repo.files
        if backend.name == "python-fastapi":
            assert "evaluate_rule" in repo.files["app/application/payroll.py"]
            assert "pub" not in repo.files.get("app/core/behavior.py", "")
            assert "def evaluate_expression" in repo.files["app/core/behavior.py"]
            assert "base_salary" in repo.files["app/domain/employee.py"]
        else:
            assert "evaluate_rule" in repo.files["src/application/payroll.rs"]
            assert "pub fn evaluate_expression" in repo.files["src/core/behavior.rs"]
            assert "base_salary" in repo.files["src/domain/employee.rs"]


@pytest.mark.parametrize(
    "plan",
    [
        CompilationPlan(
            plan_id="api-plan", isr_id="system",
            apis=[ApiOperation(
                id="api:submit", name="submit",
                behavior=ApiBehavior(
                    operation_id="submit", method="POST", path="/submit"
                ),
            )],
        ),
        CompilationPlan(
            plan_id="effect-plan", isr_id="system",
            effects=[Effect(
                id="effect:transfer", name="transfer",
                behavior=EffectBehavior(
                    effect_kind="bank_transfer", idempotent=True, idempotency_key_required=True
                ),
            )],
        ),
    ],
)
def test_api_and_effect_semantics_are_not_silently_claimed_supported(plan):
    from compiler.core.capabilities import BackendCapabilities, assert_plan_supported

    for backend in (PythonFastAPIBackend(), RustAxumBackend()):
        with pytest.raises(UnsupportedSemanticsError):
            assert_plan_supported(
                plan,
                BackendCapabilities(
                    backend_id=backend.name,
                    version=backend.version,
                    supported_features=backend.supported_features,
                ),
            )
