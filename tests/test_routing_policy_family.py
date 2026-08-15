"""D3: Routing policy family - objective ordering (Cap-D D3).

Verifies order_candidates reorders the capability-matched candidate set per
policy objective, with locality then provider_id as deterministic tie-breakers.
Ceiling behaviour is covered in test_intelligence_policy; this file covers the
ordering objectives.
"""
from tiannara.application.intelligence import (
    COST_MIN_POLICY,
    LATENCY_MIN_POLICY,
    QUALITY_MAX_POLICY,
    DEFAULT_POLICY,
    order_candidates,
)
from tiannara.domain.models.intelligence import (
    CapabilityDeclaration,
    IntelligenceResult,
    IntelligenceTask,
    LocalityLevel,
    ProviderClass,
    TaskKind,
)
from tiannara.domain.models.model_call import ModelCallRecord


def _decl(provider_id, provider_class, task_kinds=None, **profiles):
    return CapabilityDeclaration(
        provider_id=provider_id,
        provider_class=provider_class,
        task_kinds=task_kinds or [TaskKind.EXTRACTION],
        **profiles,
    )


class _Provider:
    def __init__(self, declaration):
        self._declaration = declaration

    @property
    def declaration(self):
        return self._declaration

    def complete(self, task):
        return IntelligenceResult(
            output_payload={"ok": True},
            provider_id=self._declaration.provider_id,
            provider_class=self._declaration.provider_class,
            locality=self._declaration.locality,
            model_record=ModelCallRecord(model_id=self._declaration.provider_id),
        )


def _locals(alpha_profiles, beta_profiles):
    return [
        _Provider(_decl("alpha", ProviderClass.LOCAL_MODEL, **alpha_profiles)),
        _Provider(_decl("beta", ProviderClass.LOCAL_MODEL, **beta_profiles)),
    ]


def test_order_candidates_locality_first_is_deterministic():
    candidates = _locals({}, {})  # both L2; tie-break on provider_id
    ordered = order_candidates(candidates, DEFAULT_POLICY)
    assert [p.declaration.provider_id for p in ordered] == ["alpha", "beta"]


def test_cost_min_orders_by_cost_profile():
    candidates = _locals({"cost_profile": 0.2}, {"cost_profile": 0.8})
    ordered = order_candidates(candidates, COST_MIN_POLICY)
    assert [p.declaration.provider_id for p in ordered] == ["alpha", "beta"]


def test_quality_max_orders_highest_first():
    candidates = _locals({"quality_profile": 0.3}, {"quality_profile": 0.9})
    ordered = order_candidates(candidates, QUALITY_MAX_POLICY)
    assert [p.declaration.provider_id for p in ordered] == ["beta", "alpha"]


def test_latency_min_orders_lowest_first():
    candidates = _locals({"latency_profile": 0.9}, {"latency_profile": 0.1})
    ordered = order_candidates(candidates, LATENCY_MIN_POLICY)
    assert [p.declaration.provider_id for p in ordered] == ["beta", "alpha"]
