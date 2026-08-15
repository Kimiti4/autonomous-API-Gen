"""D3: Failure cascade policy - under KEYLESS, failures stay local and bounded.

Verifies: empty candidate set -> immediate CascadeExhaustedError (no partial
calls); a local failure never escalates to a registered external provider;
the per-policy attempt budget bounds the cascade length deterministically.
"""
import pytest

from tiannara.application.intelligence import (
    CascadeExecutor,
    CascadeExhaustedError,
    KEYLESS_POLICY,
    ProviderRegistry,
    RoutingPolicy,
)
from tiannara.domain.models.intelligence import (
    CapabilityDeclaration,
    IntelligenceResult,
    IntelligenceTask,
    LocalityLevel,
    ProviderClass,
    TaskKind,
)
from tiannara.domain.models.model_call import LanguageModelError, ModelCallRecord


def _decl(provider_id, provider_class, task_kinds=None):
    return CapabilityDeclaration(
        provider_id=provider_id,
        provider_class=provider_class,
        task_kinds=task_kinds or [TaskKind.EXTRACTION],
    )


def _task(kind=TaskKind.EXTRACTION):
    return IntelligenceTask(task_kind=kind, task_label="t", prompt="p", output_schema_id="s.v1")


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
        return IntelligenceResult(
            output_payload={"ok": True},
            provider_id=self._declaration.provider_id,
            provider_class=self._declaration.provider_class,
            locality=self._declaration.locality,
            model_record=ModelCallRecord(model_id=self._declaration.provider_id),
        )


def test_empty_registry_raises_with_empty_path():
    registry = ProviderRegistry()
    with pytest.raises(CascadeExhaustedError) as exc_info:
        CascadeExecutor(registry).execute(_task(), KEYLESS_POLICY)
    assert exc_info.value.cascade_path == []


def test_failing_local_does_not_escalate_to_external():
    registry = ProviderRegistry()
    registry.register(_Provider(_decl("local-fails", ProviderClass.LOCAL_MODEL), fail=True))
    remote = _Provider(_decl("frontier", ProviderClass.REMOTE_MODEL))
    registry.register(remote)

    with pytest.raises(CascadeExhaustedError) as exc_info:
        CascadeExecutor(registry).execute(_task(), KEYLESS_POLICY)

    path = exc_info.value.cascade_path
    assert len(path) == 1
    assert path[0].outcome.value == "failed"
    assert path[0].provider_id == "local-fails"
    assert "frontier" not in [step.provider_id for step in path]
    assert remote.calls == 0


def test_cascade_attempt_budget_bounds_failures():
    registry = ProviderRegistry()
    for pid in ("f1", "f2", "f3"):
        registry.register(_Provider(_decl(pid, ProviderClass.LOCAL_MODEL), fail=True))

    budget_policy = RoutingPolicy(
        name="budget-test",
        max_locality=LocalityLevel.L2_LOCAL_MODEL,
        max_cascade_attempts=2,
    )
    with pytest.raises(CascadeExhaustedError) as exc_info:
        CascadeExecutor(registry).execute(_task(), budget_policy)

    path = exc_info.value.cascade_path
    outcomes = [step.outcome.value for step in path]
    assert len(path) == 3
    assert outcomes.count("failed") == 2
    assert outcomes.count("deflected") == 1
