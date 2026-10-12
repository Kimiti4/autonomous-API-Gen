from types import SimpleNamespace
from unittest.mock import patch

from constitutional_architecture.compiler.passes.validation_pass import ValidationPass
from constitutional_architecture.compiler.quality.diagnostics import DiagnosticsCollector


def context():
    return SimpleNamespace(isr=object(), diagnostics=DiagnosticsCollector())


def test_validation_exception_fails_closed():
    ctx = context()
    with patch(
        "constitutional_architecture.engine.isr_adapter.isr_to_graph",
        side_effect=RuntimeError("adapter unavailable"),
    ):
        result = ValidationPass().execute(ctx)

    assert result.success is False
    assert result.metrics["valid"] is False
    assert result.metrics["validation_unavailable"] is True
    assert ctx.diagnostics.has_errors
    assert any(d.code == "COMP-VAL-003" for d in ctx.diagnostics.errors)


def test_invalid_architecture_fails_validation():
    ctx = context()
    failed_result = SimpleNamespace(
        passed=False,
        errors=["invalid permission reference"],
        warnings=[],
    )
    with patch(
        "constitutional_architecture.engine.isr_adapter.isr_to_graph",
        return_value=object(),
    ), patch(
        "constitutional_architecture.validation.checker.ArchitecturalTypeChecker.validate",
        return_value=failed_result,
    ):
        result = ValidationPass().execute(ctx)

    assert result.success is False
    assert result.metrics["valid"] is False
    assert ctx.diagnostics.has_errors
    assert any(d.code == "COMP-VAL-001" for d in ctx.diagnostics.errors)


def test_valid_architecture_passes_validation():
    ctx = context()
    valid_result = SimpleNamespace(passed=True, errors=[], warnings=["informational warning"])
    with patch(
        "constitutional_architecture.engine.isr_adapter.isr_to_graph",
        return_value=object(),
    ), patch(
        "constitutional_architecture.validation.checker.ArchitecturalTypeChecker.validate",
        return_value=valid_result,
    ):
        result = ValidationPass().execute(ctx)

    assert result.success is True
    assert result.metrics["valid"] is True
    assert result.metrics["warnings"] == 1
    assert not ctx.diagnostics.has_errors