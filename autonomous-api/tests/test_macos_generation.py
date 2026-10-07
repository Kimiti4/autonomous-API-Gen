from app.engine.desktop_build import DesktopBuildPhase, create_desktop_build_request
from app.engine.desktop_target import DesktopArtifact, DesktopTarget
from app.engine.macos_generation import create_macos_generation_request, validate_macos_generation_result

def build(target=DesktopTarget.MACOS, artifact=DesktopArtifact.MACOS_APP):
    return create_desktop_build_request(build_id="build-1", workspace_id="workspace-1", target=target, artifact=artifact, phase=DesktopBuildPhase.PACKAGE, command=("authorized-builder","package"), expected_artifact_path="dist/App.app")

def test_macos_generation_requires_macos_target_and_host():
    assert create_macos_generation_request(generation_id="gen-1", build=build(), host_identity="macos-14").digest()

def test_macos_generation_rejects_non_macos_host():
    try: create_macos_generation_request(generation_id="gen-2", build=build(), host_identity="windows-2025")
    except ValueError as exc: assert str(exc) == "macos-generation-requires-macos-host"
    else: raise AssertionError("non-macOS host was accepted")

def test_macos_generation_rejects_windows_target():
    windows=build(DesktopTarget.WINDOWS, DesktopArtifact.WINDOWS_INSTALLER)
    try: create_macos_generation_request(generation_id="gen-3", build=windows, host_identity="macos-14")
    except ValueError as exc: assert str(exc) == "macos-generation-requires-macos-target"
    else: raise AssertionError("Windows target was accepted")

def test_macos_generation_result_binds_to_request():
    request=create_macos_generation_request(generation_id="gen-4", build=build(artifact=DesktopArtifact.MACOS_DMG), host_identity="macos-14")
    validate_macos_generation_result(request, generation_id="gen-4", request_digest=request.digest(), artifact_digest="sha256:artifact")
