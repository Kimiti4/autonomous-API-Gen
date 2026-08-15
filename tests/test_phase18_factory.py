"""Phase 18 -- SoftwareFactory orchestrator (hermetic fakes)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tiannara.application.factory import (
    NullRepairProvider,
    RematerializationRepairProvider,
    SoftwareFactory,
    SoftwareFactoryError,
)

FILES = {"svc/main.py": "print('main')\n", "svc/util.py": "X = 1\n"}


class _Result:
    system_name = "svc"
    backend_id = "stub_backend"
    files = FILES
    capability_manifest = {"capabilities": []}


class _Outcome:
    result = _Result()
    status = "success"


class _CompilationReport:
    statement_hash = "stmt"
    isr_hash = "isr"
    plan_id = "plan"
    policy_name = "default"
    outcomes = [_Outcome()]
    ok = True


class _Bundle:
    def __init__(self, path):
        self.path = path
        self.project_id = "svc"


class _Materialization:
    def __init__(self, bundles):
        self.bundles = bundles
        self.out_root = None
        self.commit = None
        self.manifest_path = None


class _Materializer:
    def __init__(self, root, skip=()):
        self._root = Path(root)
        self._skip = set(skip)

    def materialize(self, report, out_root=None, force=False):
        for rel, content in FILES.items():
            if rel in self._skip:
                continue
            target = self._root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        return _Materialization([_Bundle(self._root)])


class _Compiler:
    def compile_intent(self, statement, hints=None):
        return _CompilationReport()


class _Static:
    def __init__(self, ok, missing_files=()):
        self.ok = ok
        self.missing_files = list(missing_files)
        self.syntax_errors = []
        self.dependency_violations = []


class _PresenceVerifier:
    def __init__(self, required):
        self._required = required

    def verify(self, root):
        root = Path(root)
        missing = [r for r in self._required if not (root / r).exists()]
        return _Static(ok=not missing, missing_files=missing)


class _TestResult:
    passed = True
    exit_code = 0


class _ExecEnv:
    async def run_verification(self, bundle):
        return _TestResult()


class _FailingEnv:
    async def run_verification(self, bundle):
        raise RuntimeError("docker boom")


def _verifier_factory(compilation_result):
    return _PresenceVerifier(sorted(compilation_result.files.keys()))


def test_factory_happy_path(tmp_path):
    factory = SoftwareFactory(
        project_compiler=_Compiler(),
        materializer=_Materializer(tmp_path),
        execution_environment=_ExecEnv(),
        repair_provider=NullRepairProvider(),
        verifier_factory=_verifier_factory,
    )
    report = factory.run("build svc", out_root=str(tmp_path))
    assert report.ok is True
    assert report.statement_hash == "stmt"
    assert report.isr_hash == "isr"
    assert report.plan_id == "plan"
    assert report.policy_name == "default"
    outcome = report.verification_outcomes[0]
    assert outcome.repair_attempts == 0
    assert outcome.repaired is False
    assert getattr(report.fitness, "metrics")["verification"] == 1.0


def test_factory_repairs_missing_file(tmp_path):
    factory = SoftwareFactory(
        project_compiler=_Compiler(),
        materializer=_Materializer(tmp_path, skip={"svc/util.py"}),
        execution_environment=_ExecEnv(),
        repair_provider=RematerializationRepairProvider(),
        verifier_factory=_verifier_factory,
        max_repair_attempts=2,
    )
    report = factory.run("build svc", out_root=str(tmp_path))
    outcome = report.verification_outcomes[0]
    assert report.ok is True
    assert outcome.repaired is True
    assert outcome.repair_attempts >= 1
    assert (tmp_path / "svc" / "util.py").exists()


def test_factory_fails_loud_without_repair(tmp_path):
    factory = SoftwareFactory(
        project_compiler=_Compiler(),
        materializer=_Materializer(tmp_path, skip={"svc/util.py"}),
        execution_environment=_ExecEnv(),
        repair_provider=NullRepairProvider(),
        verifier_factory=_verifier_factory,
    )
    with pytest.raises(SoftwareFactoryError) as exc:
        factory.run("build svc", out_root=str(tmp_path))
    assert exc.value.report is not None
    assert exc.value.report.ok is False
    assert (tmp_path / "svc" / "util.py").exists() is False


def test_factory_isolation_from_environment_errors(tmp_path):
    factory = SoftwareFactory(
        project_compiler=_Compiler(),
        materializer=_Materializer(tmp_path),
        execution_environment=_FailingEnv(),
        repair_provider=NullRepairProvider(),
        verifier_factory=_verifier_factory,
    )
    with pytest.raises(SoftwareFactoryError):
        factory.run("build svc", out_root=str(tmp_path))
