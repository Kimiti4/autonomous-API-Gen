import pytest

from tiannara.domain.models.intelligence import (
    CapabilityDeclaration,
    IntelligenceTask,
    PrivacyClass,
    ProviderClass,
    TaskKind,
)
from tiannara.application.intelligence import ProviderRegistry, RegistryError


class _Stub:
    def __init__(self, declaration):
        self._declaration = declaration

    @property
    def declaration(self):
        return self._declaration

    def complete(self, task):
        raise AssertionError("not used in registry tests")


def _decl(provider_id, provider_class, kinds=None):
    return CapabilityDeclaration(
        provider_id=provider_id,
        provider_class=provider_class,
        task_kinds=kinds or [TaskKind.EXTRACTION],
    )


def _task(kind=TaskKind.EXTRACTION, privacy=PrivacyClass.INTERNAL):
    return IntelligenceTask(
        task_kind=kind, task_label="t", prompt="p",
        output_schema_id="s.v1", privacy_class=privacy,
    )


def test_capability_and_locality_filtering_is_deterministic():
    registry = ProviderRegistry()
    registry.register(_Stub(_decl("remote-b", ProviderClass.REMOTE_MODEL)))
    registry.register(_Stub(_decl("local-a", ProviderClass.LOCAL_MODEL)))
    registry.register(_Stub(_decl("det-a", ProviderClass.DETERMINISTIC_COMPILER)))

    from tiannara.domain.models.intelligence import LocalityLevel

    matched = registry.matches(_task(), LocalityLevel.L3_EXTERNAL_MODEL)
    assert [p.declaration.provider_id for p in matched] == [
        "det-a", "local-a", "remote-b"
    ]
    keyless = registry.matches(_task(), LocalityLevel.L2_LOCAL_MODEL)
    assert [p.declaration.provider_id for p in keyless] == ["det-a", "local-a"]


def test_privacy_local_only_caps_even_with_l3_policy():
    registry = ProviderRegistry()
    registry.register(_Stub(_decl("remote-only", ProviderClass.REMOTE_MODEL)))
    from tiannara.domain.models.intelligence import LocalityLevel

    assert registry.matches(
        _task(privacy=PrivacyClass.LOCAL_ONLY), LocalityLevel.L3_EXTERNAL_MODEL
    ) == []


def test_duplicate_provider_id_rejected():
    registry = ProviderRegistry()
    registry.register(_Stub(_decl("x", ProviderClass.ALGORITHMIC)))
    with pytest.raises(RegistryError):
        registry.register(_Stub(_decl("x", ProviderClass.ALGORITHMIC)))
