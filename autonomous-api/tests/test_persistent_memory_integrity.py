import json
import sys
from pathlib import Path

import pytest

from app.engine.memory import EvolutionMemory

# Knowledge persistence lives at the workspace root; CI runs pytest from
# autonomous-api/ with pythonpath=["."] only, so bootstrap the root package.
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def test_evolution_memory_write_is_recoverable(tmp_path):
    path = tmp_path / "memory.json"
    memory = EvolutionMemory(str(path))
    memory._save()

    loaded = json.loads(path.read_text())
    assert loaded["statistics"]["total_runs"] == 0
    assert not list(tmp_path.glob(".memory-*.tmp"))


def test_corrupt_evolution_memory_fails_closed(tmp_path):
    path = tmp_path / "memory.json"
    path.write_text("{not valid json")

    with pytest.raises(RuntimeError, match="Persistent evolution memory is unreadable"):
        EvolutionMemory(str(path))


def test_knowledge_persistence_write_is_atomic(tmp_path):
    from constitutional_architecture.knowledge.persistence import KnowledgePersistence

    persistence = KnowledgePersistence(tmp_path)
    persistence.save_fitness_records([])
    path = tmp_path / "fitness_records.json"

    assert json.loads(path.read_text()) == []
    assert not list(tmp_path.glob(".fitness_records.json.*.tmp"))


def test_corrupt_knowledge_persistence_fails_closed(tmp_path):
    from constitutional_architecture.knowledge.persistence import KnowledgePersistence

    persistence = KnowledgePersistence(tmp_path)
    (tmp_path / "fitness_records.json").write_text("{not valid json")

    with pytest.raises(RuntimeError, match="Persistent knowledge record is unreadable"):
        persistence.load_fitness_records()
