import json

import pytest
from sqlalchemy import create_engine, text

from app.core.governance.audit import AuditIntegrityError
from app.core.memory_clear import CONFIRMATION, MemoryClearAuditStore, clear_elite_memory
from app.core.config import get_settings
from app.engine.adaptive import AdaptiveMutator
from app.engine.memory import EvolutionMemory
from app.storage.migrations import migrate


def _db(tmp_path):
    db = create_engine(f"sqlite:///{tmp_path / 'clear.db'}")
    migrate(db)
    return db


def test_clear_requires_explicit_confirmation(tmp_path, monkeypatch):
    import app.core.memory_clear as module

    monkeypatch.setattr(module, "engine", _db(tmp_path))
    memory = EvolutionMemory(str(tmp_path / "memory.json"))
    memory._save()
    with pytest.raises(PermissionError):
        clear_elite_memory(
            memory=memory,
            adaptive_mutator=AdaptiveMutator(),
            actor="admin",
            confirmation="CLEAR",
        )
    assert json.loads((tmp_path / "memory.json").read_text())["statistics"]["total_runs"] == 0
    with module.engine.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM memory_clear_audit")).scalar_one() == 0


def test_clear_creates_verified_backup_and_durable_audit(tmp_path, monkeypatch):
    import app.core.memory_clear as module

    db = _db(tmp_path)
    monkeypatch.setattr(module, "engine", db)
    memory_path = tmp_path / "memory.json"
    memory = EvolutionMemory(str(memory_path))
    memory.record_run({"auth": "jwt"}, 0.9, 0.1, 1, "run-1")
    mutator = AdaptiveMutator()
    mutator.update({"auth": "jwt"}, 0.9)

    result = clear_elite_memory(
        memory=memory,
        adaptive_mutator=mutator,
        actor="admin",
        confirmation=CONFIRMATION,
        operation_id="019a0000-0000-7000-8000-000000000001",
    )

    assert result["status"] == "cleared"
    assert json.loads(memory_path.read_text())["statistics"]["total_runs"] == 0
    assert mutator.mutation_history == []
    assert all(value == 0.5 for value in mutator.success_bias.values())
    backup = tmp_path / "memory-backups" / "019a0000-0000-7000-8000-000000000001.json"
    assert backup.is_file()
    assert json.loads(backup.read_text())["statistics"]["total_runs"] == 1

    audit = MemoryClearAuditStore(get_settings().GOVERNANCE_AUDIT_SIGNING_KEY)
    records = audit.verify()
    assert [record.event_type for record in records] == [
        "memory.clear.requested",
        "memory.clear.backup_verified",
        "memory.clear.succeeded",
    ]


def test_clear_rejects_operation_replay(tmp_path, monkeypatch):
    import app.core.memory_clear as module

    monkeypatch.setattr(module, "engine", _db(tmp_path))
    memory = EvolutionMemory(str(tmp_path / "memory.json"))
    memory._save()
    kwargs = {
        "memory": memory,
        "adaptive_mutator": AdaptiveMutator(),
        "actor": "admin",
        "confirmation": CONFIRMATION,
        "operation_id": "019a0000-0000-7000-8000-000000000002",
    }
    clear_elite_memory(**kwargs)
    with pytest.raises(ValueError, match="already been used"):
        clear_elite_memory(**kwargs)


def test_clear_fails_closed_on_corrupt_memory(tmp_path, monkeypatch):
    import app.core.memory_clear as module

    monkeypatch.setattr(module, "engine", _db(tmp_path))
    path = tmp_path / "memory.json"
    path.write_text("{broken", encoding="utf-8")
    memory = EvolutionMemory.__new__(EvolutionMemory)
    memory.path = str(path)
    with pytest.raises(RuntimeError, match="unreadable"):
        clear_elite_memory(
            memory=memory,
            adaptive_mutator=AdaptiveMutator(),
            actor="admin",
            confirmation=CONFIRMATION,
        )
    assert not list((tmp_path / "memory-backups").glob("*.json"))


def test_memory_clear_audit_tamper_fails_closed(tmp_path, monkeypatch):
    import app.core.memory_clear as module

    db = _db(tmp_path)
    monkeypatch.setattr(module, "engine", db)
    memory = EvolutionMemory(str(tmp_path / "memory.json"))
    memory._save()
    clear_elite_memory(
        memory=memory,
        adaptive_mutator=AdaptiveMutator(),
        actor="admin",
        confirmation=CONFIRMATION,
        operation_id="019a0000-0000-7000-8000-000000000003",
    )
    with db.begin() as conn:
        conn.execute(
            text("UPDATE memory_clear_audit SET payload = '{"tampered":true}' WHERE sequence = 1")
        )
    with pytest.raises(AuditIntegrityError):
        MemoryClearAuditStore(module.get_settings().GOVERNANCE_AUDIT_SIGNING_KEY).verify()
