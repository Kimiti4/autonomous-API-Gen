"""Tests for SafetyGate."""

from constitutional_architecture.meta.platform_genome import (
    GenomeParameter,
    ParameterCategory,
    ParameterType,
    PlatformGenome,
    create_default_genome,
)
from constitutional_architecture.meta.safety_gate import SafetyCheckResult, SafetyGate


class TestSafetyCheckResult:
    def test_creation(self):
        r = SafetyCheckResult(passed=True, checks_passed=5, checks_performed=5)
        assert r.passed is True
        assert r.checks_passed == 5
        assert r.checks_performed == 5

    def test_failed_no_violations(self):
        r = SafetyCheckResult(passed=False, checks_passed=3, checks_performed=5, violations=("v1", "v2"))
        assert r.passed is False
        assert len(r.violations) == 2
        assert r.violations[0] == "v1"


class TestSafetyGate:
    def test_initial_state(self):
        gate = SafetyGate()
        assert gate.can_rollback is False

    def test_push_rollback_point(self):
        gate = SafetyGate()
        g = create_default_genome()
        gate.push_rollback_point(g)
        assert gate.can_rollback is True

    def test_rollback_returns_genome(self):
        gate = SafetyGate()
        g1 = create_default_genome()
        g2 = PlatformGenome(version=2)
        gate.push_rollback_point(g1)
        gate.push_rollback_point(g2)
        prev = gate.rollback()
        assert prev is not None
        assert prev.version == g2.version

    def test_rollback_returns_none_if_empty(self):
        gate = SafetyGate()
        assert gate.rollback() is None

    def test_check_mutation_safety_passes_for_minor_change(self):
        gate = SafetyGate()
        g1 = create_default_genome()
        params = dict(g1.parameters)
        params["test.x"] = GenomeParameter("test.x", "x", ParameterCategory.COMPILER,
                                           ParameterType.INT, 5)
        g2 = PlatformGenome(version=2, parent_hash=g1.content_hash, parameters=params)
        result = gate.check_mutation_safety(g1, g2)
        assert result.passed is True

    def test_check_mutation_safety_fails_if_locked_param_modified(self):
        gate = SafetyGate()
        g1_params = dict(create_default_genome().parameters)
        locked_p = GenomeParameter("locked.param", "locked", ParameterCategory.EVOLUTION,
                                   ParameterType.INT, 1, locked=True)
        g1_params["locked.param"] = locked_p
        g1 = PlatformGenome(version=1, parameters=g1_params)
        g2_params = dict(g1_params)
        g2_params["locked.param"] = GenomeParameter("locked.param", "locked", ParameterCategory.EVOLUTION,
                                                     ParameterType.INT, 99, locked=True)
        g2 = PlatformGenome(version=2, parent_hash=g1.content_hash, parameters=g2_params)
        result = gate.check_mutation_safety(g1, g2)
        assert result.passed is False
        assert any("locked" in v for v in result.violations)
