import hashlib
import zipfile
from pathlib import Path
from types import SimpleNamespace

from compiler.core.repository import build_repository
from certification.campaign.android_structural_runner import NativeAndroidStructuralRunner


def make_apk(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("AndroidManifest.xml", b"manifest")
        z.writestr("classes.dex", b"dex")


def test_native_runner_binds_all_stages_to_structural_candidate(tmp_path):
    repo = build_repository({"app/build.gradle.kts": "plugins {}\n", "README.md": "static"})
    commands = []

    def fake_run(command, **kwargs):
        commands.append(command)
        if command[0] == "gradle":
            make_apk(Path(kwargs["cwd"]) / "app/build/outputs/apk/debug/app-debug.apk")
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")

    result = NativeAndroidStructuralRunner(fake_run).execute(
        repo, tmp_path / "candidate", "revision-sha", "plan-sha", require_emulator=True
    )
    assert result.passed
    assert result.backend_class == "structural"
    assert result.verdict == "STRUCTURAL_CHECKS_ONLY"
    assert result.candidate_hash == repo.content_hash
    assert result.apk_hash == hashlib.sha256(
        (tmp_path / "candidate/app/build/outputs/apk/debug/app-debug.apk").read_bytes()
    ).hexdigest()
    assert [item.stage for item in result.evidence] == [
        "gradle_build", "apk_inspection", "emulator_install", "emulator_launch"
    ]
    assert [c[0] for c in commands] == ["gradle", "adb", "adb"]


def test_native_runner_fails_closed_when_gradle_fails(tmp_path):
    repo = build_repository({"README.md": "candidate"})
    result = NativeAndroidStructuralRunner(
        lambda command, **kwargs: SimpleNamespace(returncode=1, stdout="", stderr="failure")
    ).execute(repo, tmp_path / "candidate", "revision", "plan", require_emulator=True)
    assert not result.passed
    assert result.evidence[0].stage == "gradle_build"
    assert all(not item.passed for item in result.evidence)


def test_native_runner_rejects_repository_hash_mismatch(tmp_path):
    from compiler.core.repository import GeneratedRepository
    bad = GeneratedRepository(files={"README.md": "tampered"}, content_hash="wrong")
    try:
        NativeAndroidStructuralRunner().execute(bad, tmp_path / "candidate", "revision", "plan")
    except ValueError as exc:
        assert "content hash" in str(exc)
    else:
        raise AssertionError("tampered repository accepted")


def test_native_runner_requires_source_and_plan_hashes(tmp_path):
    repo = build_repository({"README.md": "candidate"})
    try:
        NativeAndroidStructuralRunner().execute(repo, tmp_path / "candidate", "", "plan")
    except ValueError as exc:
        assert "mandatory" in str(exc)
    else:
        raise AssertionError("unbound candidate accepted")



def _revision_fixture():
    from isr.core.graph import ISRGraph, Node, NodeType
    from isr.core.identity import Provenance
    from isr.core.revision import ISRRevision

    return ISRRevision.create(
        system_id="inventory",
        revision_id="rev:bound-test",
        schema_version="1.0",
        graph=ISRGraph(nodes={
            "dm:item": Node(
                id="dm:item", type=NodeType.DATA_MODEL,
                properties={"label": "Item"},
            )
        }),
        provenance=Provenance(
            created_by="test", created_at="2026-11-03T00:00:00Z",
            requirement_refs=["req:item"], derivation_refs=["test-fixture"],
        ),
    )


def test_execute_bound_recomputes_isr_plan_and_candidate_binding(tmp_path):
    from compiler.backends.android import compile_isr_revision

    revision = _revision_fixture()
    candidate = compile_isr_revision(revision)

    def fake_run(command, **kwargs):
        if command[0] == "gradle":
            make_apk(Path(kwargs["cwd"]) / "app/build/outputs/apk/debug/app-debug.apk")
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")

    result = NativeAndroidStructuralRunner(fake_run).execute_bound(
        revision, candidate, tmp_path / "bound-candidate", require_emulator=True
    )
    assert result.passed
    assert result.revision_hash == revision.content_hash
    assert result.plan_hash == candidate.plan_hash
    assert result.candidate_hash == candidate.repository.content_hash
    assert result.verdict == "STRUCTURAL_CHECKS_ONLY"


def test_execute_bound_rejects_candidate_from_different_revision(tmp_path):
    from dataclasses import replace
    from compiler.backends.android import compile_isr_revision

    revision = _revision_fixture()
    candidate = compile_isr_revision(revision)
    altered = replace(candidate, revision_hash="0" * 64)
    try:
        NativeAndroidStructuralRunner().execute_bound(
            revision, altered, tmp_path / "must-not-run", require_emulator=False
        )
    except ValueError as exc:
        assert "revision hash" in str(exc)
    else:
        raise AssertionError("candidate bound to another revision was accepted")
    assert not (tmp_path / "must-not-run").exists()


def test_execute_bound_rejects_tampered_candidate_repository(tmp_path):
    from dataclasses import replace
    from compiler.backends.android import compile_isr_revision

    revision = _revision_fixture()
    candidate = compile_isr_revision(revision)
    altered_repo = build_repository({**candidate.repository.files, "README.md": "tampered"})
    altered = replace(candidate, repository=altered_repo)
    try:
        NativeAndroidStructuralRunner().execute_bound(
            revision, altered, tmp_path / "must-not-run", require_emulator=False
        )
    except ValueError as exc:
        assert "canonical backend output" in str(exc)
    else:
        raise AssertionError("tampered candidate repository was accepted")
    assert not (tmp_path / "must-not-run").exists()
