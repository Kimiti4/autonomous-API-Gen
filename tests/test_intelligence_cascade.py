import pytest

from tiannara.domain.models.intelligence import (
    CapabilityDeclaration,
    CascadeStepOutcome,
    IntelligenceResult,
    IntelligenceTask,
    LocalityLevel,
    ProviderClass,
    TaskKind,
)
from tiannara.domain.models.model_call import LanguageModelError, ModelCallRecord
from tiannara.application.intelligence import (
    AutonomyAccountant,
    CascadeExecutor,
    CascadeExhaustedError,
    KEYLESS_POLICY,
    DEFAULT_POLICY,
    ProviderRegistry,
)


def _result(provider_id, locality, provider_class):
    return IntelligenceResult(
        output_payload={"ok": True},
        provider_id=provider_id,
        provider_class=provider_class,
        locality=locality,
        model_record=ModelCallRecord(model_id=provider_id),
    )


class _Provider:
    def __init__(self, declaration, fail=False):
        self._declaration = declaration
        self._fail = fail
        self.calls = 0

    @property
    def declaration(self):
        return self._declaration

    def complete(self, task):
        self.calls += 1
        if self._fail:
            raise LanguageModelError(f"{self._declaration.provider_id} failed")
        return _result(
            self._declaration.provider_id,
            self._declaration.locality,
            self._declaration.provider_class,
        )


def _decl(provider_id, provider_class):
    return CapabilityDeclaration(
        provider_id=provider_id,
        provider_class=provider_class,
        task_kinds=[TaskKind.EXTRACTION],
    )


def _task():
    return IntelligenceTask(
        task_kind=TaskKind.EXTRACTION, task_label="t", prompt="p",
        output_schema_id="s.v1",
    )


def test_deterministic_level_deflects_model_providers():
    registry = ProviderRegistry()
    det = _Provider(_decl("compiler-x", ProviderClass.DETERMINISTIC_COMPILER))
    remote = _Provider(_decl("frontier-y", ProviderClass.REMOTE_MODEL))
    registry.register(remote)
    registry.register(det)

    result = CascadeExecutor(registry).execute(_task(), DEFAULT_POLICY)
    assert result.provider_id == "compiler-x"
    assert result.locality is LocalityLevel.L0_DETERMINISTIC
    assert det.calls == 1 and remote.calls == 0

    outcomes = {step.provider_id: step.outcome for step in result.cascade_path}
    assert outcomes["compiler-x"] is CascadeStepOutcome.EXECUTED
    assert outcomes["frontier-y"] is CascadeStepOutcome.DEFLECTED


def test_cascade_falls_through_on_failure():
    registry = ProviderRegistry()
    failing = _Provider(_decl("solver-a", ProviderClass.ALGORITHMIC), fail=True)
    fallback = _Provider(_decl("local-m", ProviderClass.LOCAL_MODEL))
    registry.register(failing)
    registry.register(fallback)

    result = CascadeExecutor(registry).execute(_task(), DEFAULT_POLICY)
    assert result.provider_id == "local-m"
    outcomes = {step.provider_id: step.outcome for step in result.cascade_path}
    assert outcomes["solver-a"] is CascadeStepOutcome.FAILED
    assert outcomes["local-m"] is CascadeStepOutcome.EXECUTED


def test_keyless_policy_makes_external_unreachable():
    registry = ProviderRegistry()
    registry.register(_Provider(_decl("frontier-y", ProviderClass.REMOTE_MODEL)))
    with pytest.raises(CascadeExhaustedError) as exc_info:
        CascadeExecutor(registry).execute(_task(), KEYLESS_POLICY)
    assert exc_info.value.cascade_path == []  # never even attempted


def test_autonomy_accounting_ratios():
    registry = ProviderRegistry()
    det = _Provider(_decl("compiler-x", ProviderClass.DETERMINISTIC_COMPILER))
    remote = _Provider(_decl("frontier-y", ProviderClass.REMOTE_MODEL))
    registry.register(det)
    registry.register(remote)

    accountant = AutonomyAccountant()
    executor = CascadeExecutor(registry)
    for _ in range(3):
        accountant.observe(executor.execute(_task(), DEFAULT_POLICY))

    report = accountant.report()
    assert report["tasks_attempted"] == 3
    assert report["level_counts"]["L0"] == 3
    assert report["level_counts"]["L3"] == 0
    assert report["external_dependency_ratio"] == 0.0
    assert report["keyless_completion_ratio"] == 1.0
    assert accountant.status() == "FULL"
