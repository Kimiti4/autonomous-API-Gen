"""Phase 18 -- RepairProvider port contracts and concrete providers."""

from __future__ import annotations

from pathlib import Path

from tiannara.domain.ports.repair import (
    RepairAction,
    RepairRequest,
    RepairReport,
)


class _Static:
    def __init__(self, ok, missing_files=(), syntax_errors=(), dependency_violations=()):
        self.ok = ok
        self.missing_files = list(missing_files)
        self.syntax_errors = list(syntax_errors)
        self.dependency_violations = list(dependency_violations)


def _request(static_report, source_artifacts):
    return RepairRequest(
        bundle_path="/tmp/x",
        failure_signature="static:missing_files",
        static_report=static_report,
        test_result=None,
        source_artifacts=source_artifacts,
        attempt=1,
        max_attempts=2,
    )


def test_null_provider_diagnoses_nothing_and_applies_nothing():
    provider = NullRepairProvider()
    assert provider.diagnose(_request(_Static(False, ["a.py"]), {"a.py": "x"})) == ()
    report = provider.apply("/tmp/x", ())
    assert report.attempted is False
    assert report.applied is False
    assert report.reason is not None


def test_rematerialization_diagnoses_only_known_missing_files():
    provider = RematerializationRepairProvider()
    request = _request(
        _Static(False, ["svc/a.py", "svc/unknown.py"]),
        {"svc/a.py": "A = 1\n"},
    )
    actions = provider.diagnose(request)
    assert len(actions) == 1
    assert actions[0].target == "svc/a.py"
    assert actions[0].operation == "write_file"
    assert actions[0].content == "A = 1\n"


def test_rematerialization_apply_writes_files_to_bundle(tmp_path):
    provider = RematerializationRepairProvider()
    actions = provider.diagnose(
        _request(_Static(False, ["svc/a.py"]), {"svc/a.py": "A = 1\n"})
    )
    result = provider.apply(str(tmp_path), actions)
    assert result.applied is True
    assert (tmp_path / "svc" / "a.py").read_text(encoding="utf-8") == "A = 1\n"
    assert len(result.actions) == 1


def test_rematerialization_skips_unrepairable_missing_files():
    provider = RematerializationRepairProvider()
    actions = provider.diagnose(
        _request(_Static(False, ["svc/missing.py"]), {"svc/other.py": "y"})
    )
    assert actions == ()


def test_repair_provider_is_runtime_protocol_compatible():
    assert isinstance(NullRepairProvider(), RepairProvider)
    assert isinstance(RematerializationRepairProvider(), RepairProvider)


# -- fixtures: import concrete providers + port ------------------------------

from tiannara.application.factory.repair_providers import (  # noqa: E402
    NullRepairProvider,
    RematerializationRepairProvider,
)
from tiannara.domain.ports.repair import RepairProvider  # noqa: E402
