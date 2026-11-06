from pathlib import Path

import pytest

from compiler.errors import ArtifactPackagingError
from compiler.models import CompilationOutput, GeneratedArtifact
from compiler.packaging import ArtifactPackager
from compiler.validation import validate_compilation_output


def _output(*paths):
    return CompilationOutput(
        artifacts=[
            GeneratedArtifact(path=path, content="candidate")
            for path in paths
        ]
    )


@pytest.mark.parametrize(
    "unsafe",
    [
        "../escape.txt",
        "/absolute/escape.txt",
        "C:/absolute/escape.txt",
        r"\\server\share\escape.txt",
        r"nested\escape.txt",
        ".git/config",
        ".TIANNARA/provenance.json",
        "a//b.txt",
        "a/./b.txt",
        "artifact-manifest.json",
    ],
)
def test_packager_rejects_unsafe_paths_before_any_write(tmp_path, unsafe):
    with pytest.raises(ArtifactPackagingError):
        ArtifactPackager().package(
            _output("safe.txt", unsafe),
            "job-1",
            "test.backend",
            "1.0",
            tmp_path,
        )
    assert not (tmp_path / "safe.txt").exists()
    assert not (tmp_path.parent / "escape.txt").exists()


def test_packager_rejects_symlink_escape(tmp_path):
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir()
    (tmp_path / "link").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ArtifactPackagingError, match="symlink|escapes"):
        ArtifactPackager().package(
            _output("link/escape.txt"),
            "job-2",
            "test.backend",
            "1.0",
            tmp_path,
        )
    assert not (outside / "escape.txt").exists()


def test_packager_rejects_casefolded_path_collisions(tmp_path):
    with pytest.raises(ArtifactPackagingError, match="Duplicate artifact path"):
        ArtifactPackager().package(
            _output("src/Main.py", "src/main.py"),
            "job-3",
            "test.backend",
            "1.0",
            tmp_path,
        )
    assert not (tmp_path / "src").exists()


def test_packager_requires_fresh_output_directory(tmp_path):
    (tmp_path / "stale.txt").write_text("stale", encoding="utf-8")
    with pytest.raises(ArtifactPackagingError, match="must be empty"):
        ArtifactPackager().package(
            _output("main.py"),
            "job-4",
            "test.backend",
            "1.0",
            tmp_path,
        )
    assert (tmp_path / "stale.txt").read_text(encoding="utf-8") == "stale"


def test_output_validator_rejects_noncanonical_artifact_paths():
    report = validate_compilation_output(
        _output("good.txt", "../escape.txt", "src//bad.py", ".git/config")
    )
    assert report.valid is False
    codes = {issue.code for issue in report.issues}
    assert "ARTIFACT_UNSAFE_PATH" in codes
