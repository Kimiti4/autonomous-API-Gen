"""Phase-31 -- DockerExecutionEnvironment mount-path correctness.

Hermetic regression test for DEFECT-TRACKED: ``DockerExecutionEnvironment`` must
mount the bundle under an *absolute* host path. A relative ``bundle.path`` (as
passed by the calibration harness via a relative ``--out``) silently fails to
mount under Docker, making ``go test`` run against an empty ``/work`` dir and
report spurious runtime failures. These tests stub the subprocess (no real
Docker) so they stay green in CI regardless of Docker availability.
"""
from __future__ import annotations

import asyncio
from collections import Counter
from pathlib import Path

import tiannara.infrastructure.sandbox.docker_environment as de
from tiannara.application.harness.calibration.generator import generate_corpus
from tiannara.application.harness.calibration.harness import (
    BackendCalibrationHarness,
    build_calibration_registry,
)
from tiannara.infrastructure.ledger.jsonl_evidence_ledger import JsonlEvidenceLedger
from tiannara.infrastructure.sandbox.docker_environment import DockerExecutionEnvironment


class _FakeBundle:
    def __init__(self, path):
        self.path = Path(path)  # deliberately RELATIVE


class _FakeProc:
    stdout = None
    stderr = None

    async def wait(self, *a, **k):
        return 0

    async def read(self):
        return b""


def test_docker_mount_uses_absolute_host_path(monkeypatch):
    env = DockerExecutionEnvironment(
        test_command=["go", "test", "./..."],
        runtime_image="golang:1.22-alpine",
    )
    captured = {}

    async def fake(*cmd, **kw):
        captured["cmd"] = list(cmd)
        return _FakeProc()

    monkeypatch.setattr(de.asyncio, "create_subprocess_exec", fake)
    asyncio.run(env.run_verification(_FakeBundle("out/calibration/go_hexagonal")))

    assert captured["cmd"][:4] == ["docker", "run", "--rm", "-v"]
    host, sep, work = captured["cmd"][4].rpartition(":")
    assert sep == ":" and work == "/work", f"malformed mount arg: {captured['cmd'][4]!r}"
    assert Path(host).is_absolute(), f"host path must be absolute, got {host!r}"
    assert captured["cmd"][7] == "golang:1.22-alpine"
    assert captured["cmd"][8:] == ["go", "test", "./..."]


def test_docker_available_detects_docker_cli():
    assert isinstance(DockerExecutionEnvironment.available(), bool)


def test_calibrate_honest_degrade_when_docker_and_toolchain_absent(tmp_path, monkeypatch):
    """No docker + no go -> Go runtime degrades to skipped:toolchain_absent."""
    import shutil as sh

    monkeypatch.setattr(DockerExecutionEnvironment, "available", classmethod(lambda cls: False))
    monkeypatch.setattr(sh, "which", lambda *_a, **_k: None)

    harness = BackendCalibrationHarness(
        build_calibration_registry(), JsonlEvidenceLedger(tmp_path / "ev.jsonl")
    )
    report = harness.calibrate(corpus=generate_corpus(4, seed=0), out_root=tmp_path / "out")
    statuses = Counter(o.runtime_status for o in report.outcomes)
    # No docker + no toolchain on PATH -> both Go and FastAPI degrade honestly.
    # FastAPI now declares a runtime_image+test_command (R2.4.0a), so it no
    # longer hit skipped:no_test_command; it degrades to toolchain_absent like Go.
    assert statuses["skipped:toolchain_absent"] == 8
    assert statuses.get("skipped:no_test_command", 0) == 0
    assert report.runtime_coverage == 0.0


def test_go_runtime_engages_when_docker_present(tmp_path, monkeypatch):
    """Docker present + go toolchain in image -> runtime_status becomes 'ran'."""
    monkeypatch.setattr(DockerExecutionEnvironment, "available", classmethod(lambda cls: True))
    # Stub the docker subprocess so we don't pull images here; just record ran.
    captured = {}

    async def fake(*cmd, **kw):
        captured["cmd"] = list(cmd)

        class P:
            stdout = None
            stderr = None

            async def wait(self, *a, **k):
                return 0

            async def read(self):
                return b""

        return P()

    monkeypatch.setattr(de.asyncio, "create_subprocess_exec", fake)

    harness = BackendCalibrationHarness(
        build_calibration_registry(), JsonlEvidenceLedger(tmp_path / "ev.jsonl")
    )
    report = harness.calibrate(corpus=generate_corpus(2, seed=0), out_root=tmp_path / "out")
    by_backend = {o.backend_id: o.runtime_status for o in report.outcomes}
    assert by_backend == {
        "go_hexagonal": "ran",          # docker present + runtime_image -> ran
        "fastapi_hexagonal": "ran",     # docker present + build_phase -> ran
    }
    assert report.runtime_coverage == 1.0
