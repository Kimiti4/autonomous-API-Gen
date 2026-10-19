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
from compiler.core.plan import CompilationPlan, DataModel
from isr.core.behavior import DataModelBehavior


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
                "fields": [{"name": "salary", "value_type": "money", "precision": 12, "scale": 2}]
            }),
        )],
    )
    assert SemanticFeature.TYPED_FIELDS in required_features(plan)
    with pytest.raises(UnsupportedSemanticsError, match="typed_fields"):
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
    with pytest.raises(UnsupportedSemanticsError, match="cannot compile declared ISR semantics"):
        backend.compile(plan)
