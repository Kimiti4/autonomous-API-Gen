from app.engine.desktop_build import (
    DesktopBuildEvidence,
    DesktopBuildPhase,
    create_desktop_build_request,
    validate_desktop_build_evidence,
)
from app.engine.desktop_target import DesktopArtifact, DesktopTarget


def test_windows_build_request_accepts_windows_artifact():
    request = create_desktop_build_request(
        build_id="b1",
        workspace_id="w1",
        target=DesktopTarget.WINDOWS,
        artifact=DesktopArtifact.WINDOWS_INSTALLER,
        phase=DesktopBuildPhase.PACKAGE,
        command=("packager", "build"),
        expected_artifact_path="dist/app.exe",
    )
    assert request.target is DesktopTarget.WINDOWS
    assert request.digest()


def test_macos_build_request_accepts_macos_artifact():
    request = create_desktop_build_request(
        build_id="b2",
        workspace_id="w2",
        target=DesktopTarget.MACOS,
        artifact=DesktopArtifact.MACOS_APP,
        phase=DesktopBuildPhase.BUILD,
        command=("builder", "build"),
        expected_artifact_path="dist/App.app",
    )
    assert request.artifact is DesktopArtifact.MACOS_APP


def test_cross_target_artifact_is_rejected():
    try:
        create_desktop_build_request(
            build_id="b3",
            workspace_id="w3",
            target=DesktopTarget.WINDOWS,
            artifact=DesktopArtifact.MACOS_DMG,
            phase=DesktopBuildPhase.PACKAGE,
            command=("packager", "build"),
            expected_artifact_path="dist/App.dmg",
        )
    except ValueError as exc:
        assert str(exc).startswith("desktop-build-artifact-not-allowed:")
    else:
        raise AssertionError("cross-target artifact was accepted")


def test_evidence_must_bind_to_exact_request():
    request = create_desktop_build_request(
        build_id="b4",
        workspace_id="w4",
        target=DesktopTarget.MACOS,
        artifact=DesktopArtifact.MACOS_DMG,
        phase=DesktopBuildPhase.PACKAGE,
        command=("packager", "build"),
        expected_artifact_path="dist/App.dmg",
    )
    evidence = DesktopBuildEvidence(
        build_id="b4",
        request_digest=request.digest(),
        target=DesktopTarget.MACOS,
        artifact=DesktopArtifact.MACOS_DMG,
        platform_identity="macos-runner",
        artifact_digest="sha256:artifact",
        verification_refs=("verify-1",),
    )
    assert validate_desktop_build_evidence(request, evidence).complete


def test_evidence_from_different_request_is_rejected():
    request = create_desktop_build_request(
        build_id="b5",
        workspace_id="w5",
        target=DesktopTarget.WINDOWS,
        artifact=DesktopArtifact.WINDOWS_PORTABLE,
        phase=DesktopBuildPhase.PACKAGE,
        command=("packager", "build"),
        expected_artifact_path="dist/App.zip",
    )
    evidence = DesktopBuildEvidence(
        build_id="b5",
        request_digest="wrong",
        target=DesktopTarget.WINDOWS,
        artifact=DesktopArtifact.WINDOWS_PORTABLE,
        platform_identity="windows-runner",
        artifact_digest="sha256:artifact",
        verification_refs=("verify-1",),
    )
    try:
        validate_desktop_build_evidence(request, evidence)
    except ValueError as exc:
        assert str(exc) == "desktop-build-evidence-request-mismatch"
    else:
        raise AssertionError("unbound evidence was accepted")
