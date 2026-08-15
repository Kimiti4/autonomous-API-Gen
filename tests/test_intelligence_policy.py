"""D2: Autonomous Intelligence Runtime - policy family + certification contracts.

Pins the structural property that KEYLESS_POLICY makes external intelligence
unreachable (locality ceiling < L3), not merely unpreferred. Also binds the
policy-family table that AutonomyCertification consults.
"""
import pytest

from tiannara.application.intelligence import (
    AutonomyAccountant,
    CascadeExecutor,
    CascadeExhaustedError,
    KEYLESS_POLICY,
    DEFAULT_POLICY,
    OFFLINE_POLICY,
    PRIVACY_MAX_POLICY,
    COST_MIN_POLICY,
    LATENCY_MIN_POLICY,
    QUALITY_MAX_POLICY,
    ProviderRegistry,
    certify_no_external_dependency,
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


def _decl(provider_id, provider_class, task_kinds=None, **profiles):
    return CapabilityDeclaration(
        provider_id=provider_id,
        provider_class=provider_class,
        task_kinds=task_kinds or [TaskKind.EXTRACTION],
        **profiles,
    )


def _task(kind=TaskKind.EXTRACTION):
    return IntelligenceTask(
        task_kind=kind, task_label="t", prompt="p", output_schema_id="s.v1"
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
        return IntelligenceResult(
            output_payload={"ok": True},
            provider_id=self._declaration.provider_id,
            provider_class=self._declaration.provider_class,
            locality=self._declaration.locality,
            model_record=ModelCallRecord(model_id=self._declaration.provider_id),
        )


def test_policy_family_locality_ceilings():
    assert KEYLESS_POLICY.max_locality is LocalityLevel.L2_LOCAL_MODEL
    assert OFFLINE_POLICY.max_locality is LocalityLevel.L2_LOCAL_MODEL
    assert PRIVACY_MAX_POLICY.max_locality is LocalityLevel.L2_LOCAL_MODEL
    for policy in (DEFAULT_POLICY, COST_MIN_POLICY, LATENCY_MIN_POLICY, QUALITY_MAX_POLICY):
        assert policy.max_locality is LocalityLevel.L3_EXTERNAL_MODEL


def test_keyless_registry_matches_exclude_external():
    registry = ProviderRegistry()
    registry.register(_Provider(_decl("det", ProviderClass.DETERMINISTIC_COMPILER)))
    registry.register(_Provider(_decl("local", ProviderClass.LOCAL_MODEL)))
    registry.register(_Provider(_decl("frontier", ProviderClass.REMOTE_MODEL)))

    keyless = registry.matches(_task(), KEYLESS_POLICY.max_locality)
    default = registry.matches(_task(), DEFAULT_POLICY.max_locality)

    assert [p.declaration.provider_id for p in keyless] == ["det", "local"]
    assert "frontier" in [p.declaration.provider_id for p in default]


def test_keyless_external_structurally_unreachable():
    registry = ProviderRegistry()
    registry.register(_Provider(_decl("frontier", ProviderClass.REMOTE_MODEL)))
    with pytest.raises(CascadeExhaustedError) as exc_info:
        CascadeExecutor(registry).execute(_task(), KEYLESS_POLICY)
    assert exc_info.value.cascade_path == []


def test_keyless_autonomy_accountant_full():
    registry = ProviderRegistry()
    registry.register(_Provider(_decl("local", ProviderClass.LOCAL_MODEL)))
    registry.register(_Provider(_decl("frontier", ProviderClass.REMOTE_MODEL)))
    executor = CascadeExecutor(registry)

    accountant = AutonomyAccountant()
    for _ in range(3):
        accountant.observe(executor.execute(_task(), KEYLESS_POLICY))

    report = accountant.report()
    assert report["tasks_attempted"] == 3
    assert report["level_counts"]["L3"] == 0
    assert report["keyless_completion_ratio"] == 1.0
    assert report["external_dependency_ratio"] == 0.0
    assert accountant.status() == "FULL"


def test_certify_excludes_external_under_keyless():
    registry = ProviderRegistry()
    registry.register(
        _Provider(
            _decl(
                "local",
                ProviderClass.LOCAL_MODEL,
                task_kinds=[TaskKind.EXTRACTION, TaskKind.SYNTHESIS],
            )
        )
    )
    cert = certify_no_external_dependency(
        registry, KEYLESS_POLICY, [TaskKind.EXTRACTION, TaskKind.SYNTHESIS]
    )
    assert cert.external_api_key_required is False
    assert cert.policy_name == "keyless"
    assert cert.max_locality is LocalityLevel.L2_LOCAL_MODEL
    assert all(cert.per_task_coverage.values())


def test_certify_detects_missing_non_external_under_default():
    registry = ProviderRegistry()
    registry.register(
        _Provider(_decl("frontier", ProviderClass.REMOTE_MODEL, task_kinds=[TaskKind.EXTRACTION]))
    )
    cert = certify_no_external_dependency(registry, DEFAULT_POLICY, [TaskKind.EXTRACTION])
    assert cert.external_api_key_required is True
