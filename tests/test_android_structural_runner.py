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
