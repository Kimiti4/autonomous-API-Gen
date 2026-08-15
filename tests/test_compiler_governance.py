"""
Tests for Phase 25.3 compiler governance and production gating.
"""

from pathlib import Path

import pytest

from compiler.backends.reference_backend import ReferenceBackend
from compiler.governance.client import StaticGovernanceClient
from compiler.governance.compiler import (
    CompilationGovernanceError,
    GovernedCompiler,
)
from compiler.governance.enforcer import CompilerGovernanceEnforcer
from compiler.governance.models import CompilerGovernancePolicy
from compiler.kernel import UniversalCompiler
from compiler.models import CompilationRequest, CompilationTarget
from compiler.registry import BackendRegistry
from compiler.sdk.certification import BackendCertificationEngine
from compiler.sdk.models import BackendCertificationRequest


def minimal_isr() -> dict:
    return {
        "isr_id": "isr_governance_test",
        "version": "1.0.0",
        "name": "Governance Test System",
    }


def build_environment(tmp_path: Path, governance_decision: str = "ALLOW"):
    registry = BackendRegistry()
    registry.register_backend(ReferenceBackend())

    certification_engine = BackendCertificationEngine(registry)

    compiler = UniversalCompiler(
        registry=registry,
        output_root=tmp_path,
    )

    governance_client = StaticGovernanceClient(
        decision=governance_decision,
        reason="Static governance decision.",
    )

    policy = CompilerGovernancePolicy(
        production_environments=["production"],
        certified_required_environments=["production", "staging"],
        allow_uncertified_development=True,
        require_governance_for_production=True,
        fail_closed_on_governance_unavailable=True,
        max_certification_age_days=90,
    )

    enforcer = CompilerGovernanceEnforcer(
        registry=registry,
        certification_engine=certification_engine,
        governance_client=governance_client,
        policy=policy,
    )

    governed_compiler = GovernedCompiler(
        inner=compiler,
        enforcer=enforcer,
    )

    return {
        "registry": registry,
        "certification_engine": certification_engine,
        "compiler": compiler,
        "governed_compiler": governed_compiler,
        "enforcer": enforcer,
    }


def test_development_allows_uncertified_backend(tmp_path: Path):
    env = build_environment(tmp_path)

    request = CompilationRequest(
        isr=minimal_isr(),
        target=CompilationTarget(
            backend_id="reference.summary",
        ),
        environment="development",
    )

    result = env["governed_compiler"].compile(request)

    assert result.status == "SUCCEEDED"


def test_production_denies_uncertified_backend(tmp_path: Path):
    env = build_environment(tmp_path)

    request = CompilationRequest(
        isr=minimal_isr(),
        target=CompilationTarget(
            backend_id="reference.summary",
        ),
        environment="production",
    )

    with pytest.raises(CompilationGovernanceError):
        env["governed_compiler"].compile(request)


def test_production_allows_certified_backend(tmp_path: Path):
    env = build_environment(tmp_path)

    env["certification_engine"].certify(
        BackendCertificationRequest(
            backend_id="reference.summary",
        )
    )

    request = CompilationRequest(
        isr=minimal_isr(),
        target=CompilationTarget(
            backend_id="reference.summary",
        ),
        environment="production",
    )

    result = env["governed_compiler"].compile(request)

    assert result.status == "SUCCEEDED"


def test_production_denies_revoked_backend(tmp_path: Path):
    env = build_environment(tmp_path)

    env["certification_engine"].certify(
        BackendCertificationRequest(
            backend_id="reference.summary",
        )
    )

    env["certification_engine"].revoke(
        backend_id="reference.summary",
        reason="Test revocation.",
    )

    request = CompilationRequest(
        isr=minimal_isr(),
        target=CompilationTarget(
            backend_id="reference.summary",
        ),
        environment="production",
    )

    with pytest.raises(CompilationGovernanceError):
        env["governed_compiler"].compile(request)


def test_production_denies_when_governance_denies(tmp_path: Path):
    env = build_environment(tmp_path, governance_decision="DENY")

    env["certification_engine"].certify(
        BackendCertificationRequest(
            backend_id="reference.summary",
        )
    )

    request = CompilationRequest(
        isr=minimal_isr(),
        target=CompilationTarget(
            backend_id="reference.summary",
        ),
        environment="production",
    )

    with pytest.raises(CompilationGovernanceError):
        env["governed_compiler"].compile(request)


def test_production_denies_when_governance_unavailable(tmp_path: Path):
    env = build_environment(tmp_path)

    env["certification_engine"].certify(
        BackendCertificationRequest(
            backend_id="reference.summary",
        )
    )

    env["enforcer"].governance_client = None

    request = CompilationRequest(
        isr=minimal_isr(),
        target=CompilationTarget(
            backend_id="reference.summary",
        ),
        environment="production",
    )

    with pytest.raises(CompilationGovernanceError):
        env["governed_compiler"].compile(request)
