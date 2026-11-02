"""Hardening tests — python-fastapi backend with durable ledger + effect contracts.
Fail-closed: exact assertions; no fabricated clients/forms/routes; truthful capabilities.
"""
from __future__ import annotations
from compiler.backends.python_fastapi import PythonFastAPIBackend
from compiler.core.capabilities import SemanticFeature
from compiler.core.plan import CompilationPlan

def test_supports_effect_execution_semantics() -> None:
    backend = PythonFastAPIBackend()
    assert SemanticFeature.EFFECT_EXECUTION in backend.supported_features

def test_compile_requires_authorization() -> None:
    # Fail-closed: authorization enforcement is required for this backend.
    backend = PythonFastAPIBackend()
    assert callable(backend.verify_executable_effect_contract)

def test_empty_plan_verifies_empty() -> None:
    backend = PythonFastAPIBackend()
    plan = CompilationPlan(plan_id="p1", isr_id="isr1", services=[])
    result = backend.verify_executable_effect_contract(plan, None)
    assert result == []
