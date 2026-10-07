import pytest

from app.engine.desktop_target import (
    DesktopArtifact,
    DesktopTarget,
    DesktopTargetContract,
)


@pytest.mark.parametrize(
    ("target", "artifacts"),
    [
        (DesktopTarget.WINDOWS, {DesktopArtifact.WINDOWS_INSTALLER, DesktopArtifact.WINDOWS_PORTABLE}),
        (DesktopTarget.MACOS, {DesktopArtifact.MACOS_APP, DesktopArtifact.MACOS_DMG}),
    ],
)
def test_desktop_targets_have_explicit_artifact_boundaries(target, artifacts):
    contract = DesktopTargetContract.for_target(target)
    assert set(contract.allowed_artifacts) == artifacts


def test_windows_cannot_emit_macos_artifacts():
    contract = DesktopTargetContract.for_target(DesktopTarget.WINDOWS)
    assert not contract.allows_artifact(DesktopArtifact.MACOS_APP)
    assert not contract.allows_artifact(DesktopArtifact.MACOS_DMG)


def test_macos_cannot_emit_windows_artifacts():
    contract = DesktopTargetContract.for_target(DesktopTarget.MACOS)
    assert not contract.allows_artifact(DesktopArtifact.WINDOWS_INSTALLER)
    assert not contract.allows_artifact(DesktopArtifact.WINDOWS_PORTABLE)


def test_invalid_target_and_artifact_fail_closed():
    with pytest.raises(ValueError, match="invalid-desktop-target"):
        DesktopTargetContract.for_target("linux")
    with pytest.raises(ValueError, match="invalid-desktop-artifact"):
        DesktopTargetContract.for_target(DesktopTarget.WINDOWS).allows_artifact("deb")


def test_release_requires_explicit_human_authorization():
    contract = DesktopTargetContract.for_target(DesktopTarget.WINDOWS)
    with pytest.raises(ValueError, match="desktop-release-authorization-required"):
        contract.validate_release_authorization(False)
    contract.validate_release_authorization(True)
