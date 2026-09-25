import json
from pathlib import Path

import pytest

from app.engine.backend_contract import CompiledArtifact
from app.engine.backends import materialize
from app.storage.atomic import atomic_write_json


def test_atomic_json_write_preserves_previous_file_on_serialization_failure(tmp_path):
    path = tmp_path / "state.json"
    atomic_write_json(path, {"version": 1})

    class Unserializable:
        pass

    with pytest.raises(TypeError):
        atomic_write_json(path, {"bad": Unserializable()})

    assert json.loads(path.read_text(encoding="utf-8")) == {"version": 1}
    assert not list(tmp_path.glob(".state.json.*.tmp"))


def test_materialize_replaces_tree_as_one_publication(tmp_path):
    output = tmp_path / "generated"
    output.mkdir()
    (output / "stale.py").write_text("stale", encoding="utf-8")

    artifact = CompiledArtifact(
        backend_id="test",
        files={"main.py": "new", "nested/config.txt": "config"},
        metadata={"architecture_hash": "arch-test"},
    )

    result = materialize(artifact, str(output))

    assert Path(result) == output
    assert (output / "main.py").read_text(encoding="utf-8") == "new"
    assert (output / "nested/config.txt").read_text(encoding="utf-8") == "config"
    assert not (output / "stale.py").exists()
    assert (output / "artifact-manifest.json").exists()
    assert not list(tmp_path.glob(".generated.materialize-previous"))


def test_materialize_failure_does_not_replace_live_tree(tmp_path, monkeypatch):
    output = tmp_path / "generated"
    output.mkdir()
    (output / "live.py").write_text("live", encoding="utf-8")

    artifact = CompiledArtifact(
        backend_id="test",
        files={"new.py": "new"},
        metadata={"architecture_hash": "arch-test"},
    )

    original_write_text = Path.write_text

    def fail_manifest(self, data, *args, **kwargs):
        if self.name == "artifact-manifest.json":
            raise OSError("manifest write failed")
        return original_write_text(self, data, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", fail_manifest)

    with pytest.raises(OSError, match="manifest write failed"):
        materialize(artifact, str(output))

    assert (output / "live.py").read_text(encoding="utf-8") == "live"
    assert not (output / "new.py").exists()
    assert not list(tmp_path.glob(".generated.*"))


def test_materialize_validation_failure_does_not_replace_live_tree(tmp_path, monkeypatch):
    output = tmp_path / "generated"
    output.mkdir()
    (output / "live.py").write_text("live", encoding="utf-8")

    artifact = CompiledArtifact(
        backend_id="test",
        files={"new.py": "new"},
        metadata={"architecture_hash": "arch-test"},
    )

    def fail_validation(*args, **kwargs):
        raise ValueError("staged verification failed")

    monkeypatch.setattr("app.engine.backends._validate_verified_artifact", fail_validation)

    with pytest.raises(ValueError, match="staged verification failed"):
        materialize(artifact, str(output))

    assert (output / "live.py").read_text(encoding="utf-8") == "live"
    assert not (output / "new.py").exists()
    assert not list(tmp_path.glob(".generated.*"))


def test_persistent_memory_save_is_atomic_and_load_fails_closed(tmp_path, monkeypatch):
    import app.models.memory as models_memory

    target = tmp_path / "memory.json"
    monkeypatch.setattr("app.models.memory.FILE", str(target))
    models_memory.save({"version": 1})

    class Unserializable:
        pass

    with pytest.raises(TypeError):
        models_memory.save({"bad": Unserializable()})

    assert json.loads(target.read_text(encoding="utf-8")) == {"version": 1}
    assert not list(tmp_path.glob(".memory.json.*.tmp"))

    monkeypatch.setattr("app.models.memory.FILE", str(tmp_path / "missing.json"))
    assert models_memory.load() == {}

    corrupt = tmp_path / "corrupt.json"
    corrupt.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr("app.models.memory.FILE", str(corrupt))
    with pytest.raises(RuntimeError, match="unreadable"):
        models_memory.load()
