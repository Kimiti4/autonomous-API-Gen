from pathlib import Path

import pytest

from tiannara.application.compiler.writer import write_bundle
from tiannara.domain.models.capability_manifest import CapabilityManifest
from tiannara.domain.models.compilation import CompilationResult


def _result(files):
    return CompilationResult(
        backend_id="test-backend",
        system_name="test-system",
        files=files,
        capability_manifest=CapabilityManifest(
            backend_id="test-backend", capabilities=[]
        ),
    )


@pytest.mark.parametrize(
    "unsafe",
    [
        "../escape.txt",
        "nested/../../escape.txt",
        "/absolute/escape.txt",
        "C:/absolute/escape.txt",
        r"\\server\share\escape.txt",
        r"nested\escape.txt",
        "",
    ],
)
def test_writer_rejects_unsafe_paths_before_writing_any_file(tmp_path, unsafe):
    with pytest.raises(ValueError, match="unsafe generated path"):
        write_bundle(
            _result({"safe.txt": "must not be written", unsafe: "escape"}),
            tmp_path,
        )
    assert not (tmp_path / "safe.txt").exists()


def test_writer_rejects_symlink_parent_escape(tmp_path):
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir()
    (tmp_path / "link").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink|escapes"):
        write_bundle(_result({"link/escape.txt": "no"}), tmp_path)
    assert not (outside / "escape.txt").exists()


def test_writer_accepts_nested_relative_files(tmp_path):
    write_bundle(_result({"src/main.py": "print('ok')"}), tmp_path)
    assert (tmp_path / "src" / "main.py").read_text(encoding="utf-8") == "print('ok')"
