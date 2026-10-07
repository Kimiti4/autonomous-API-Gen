import pytest
from app.engine.desktop_build import DesktopBuildEvidence, DesktopBuildPhase, create_desktop_build_request
from app.engine.desktop_target import DesktopArtifact, DesktopTarget
from app.engine.desktop_release import DesktopReleaseAction, DesktopReleaseAuthorization, assess_desktop_release

def request():
    return create_desktop_build_request(build_id="b1",workspace_id="w1",target=DesktopTarget.MACOS,
        artifact=DesktopArtifact.MACOS_APP,phase=DesktopBuildPhase.PACKAGE,
        command=("python","-c","print('build')"),expected_artifact_path="dist/App.app")

def evidence(r):
    return DesktopBuildEvidence(r.build_id,r.digest(),r.target,r.artifact,"macos-14","a"*64,("verify-1",))

def test_release_is_not_production_ready_for_consequential_actions_without_human_authorization():
    r=request(); result=assess_desktop_release(r,evidence(r),artifact_digest="a"*64,
        required_actions=(DesktopReleaseAction.SIGN,DesktopReleaseAction.NOTARIZE))
    assert not result.production_ready
    assert "human-release-authorization-required" in result.reasons

def test_authorized_release_actions_can_be_ready():
    r=request(); auth=DesktopReleaseAuthorization("auth-1","human-operator",DesktopTarget.MACOS,"a"*64,
        (DesktopReleaseAction.SIGN,DesktopReleaseAction.NOTARIZE,DesktopReleaseAction.DISTRIBUTE))
    result=assess_desktop_release(r,evidence(r),artifact_digest="a"*64,authorization=auth,
        required_actions=(DesktopReleaseAction.SIGN,DesktopReleaseAction.NOTARIZE))
    assert result.production_ready
    assert len(result.digest)==64

def test_wrong_target_or_artifact_authorization_fails_closed():
    r=request(); auth=DesktopReleaseAuthorization("auth-2","human",DesktopTarget.WINDOWS,"a"*64,(DesktopReleaseAction.SIGN,))
    result=assess_desktop_release(r,evidence(r),artifact_digest="a"*64,authorization=auth,required_actions=(DesktopReleaseAction.SIGN,))
    assert not result.production_ready
