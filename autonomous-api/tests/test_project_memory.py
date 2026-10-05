from pathlib import Path

import pytest

from app.engine.project_memory import ProjectMemory, ProjectMemoryStore


def test_memory_is_content_addressed_and_chainable() -> None:
    store = ProjectMemoryStore()
    first = ProjectMemory.create(
        project_id="p1", kind="requirement", statement="Ship login",
        status="authoritative", source="user",
    )
    store.append(first)
    second = ProjectMemory.create(
        project_id="p1", kind="observation", statement="Login E2E passed",
        status="observed", source="e2e-run", evidence=("run:123",),
        parent_digest=store.head_digest,
    )
    store.append(second)

    assert first.verify_digest()
    assert second.verify_digest()
    assert second.parent_digest == first.digest
    assert store.head_digest == second.digest


def test_verified_memory_requires_evidence() -> None:
    with pytest.raises(ValueError, match="verified-memory-requires-evidence"):
        ProjectMemory.create(
            project_id="p1", kind="observation", statement="Passed",
            status="observed", source="system",
        )


def test_advisory_memory_cannot_be_recast_as_project_truth() -> None:
    store = ProjectMemoryStore()
    advisory = ProjectMemory.create(
        project_id="p1", kind="advisory", statement="Consider caching",
        status="advisory", source="learned-pattern",
    )
    store.append(advisory)

    assert store.current() == ()
    assert store.context()["advisory"] == (advisory,)
    assert store.context()["authoritative"] == ()


def test_supersession_is_explicit_and_current_context_hides_old_record() -> None:
    store = ProjectMemoryStore()
    old = ProjectMemory.create(
        project_id="p1", kind="constraint", statement="Use current contract",
        status="authoritative", source="user",
    )
    store.append(old)
    new = store.supersede(
        old, statement="Use revised contract", source="user",
        status="authoritative",
    )

    assert store.current() == (new,)
    assert new.supersedes == old.memory_id


def test_wrong_parent_is_rejected() -> None:
    store = ProjectMemoryStore()
    entry = ProjectMemory.create(
        project_id="p1", kind="decision", statement="Decision",
        status="authoritative", source="user", parent_digest="not-head",
    )
    with pytest.raises(ValueError, match="memory-parent-digest-mismatch"):
        store.append(entry)


def test_persistence_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "memory.jsonl"
    store = ProjectMemoryStore()
    entry = ProjectMemory.create(
        project_id="p1", kind="certification", statement="Release certified",
        status="certified", source="gate", evidence=("sha256:e1",),
    )
    store.append(entry)
    store.persist(path)

    loaded = ProjectMemoryStore.load(path)
    assert loaded.entries == store.entries
    assert loaded.head_digest == store.head_digest


def test_tampering_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "memory.jsonl"
    store = ProjectMemoryStore()
    entry = ProjectMemory.create(
        project_id="p1", kind="observation", statement="Observed",
        status="observed", source="test", evidence=("e1",),
    )
    store.append(entry)
    store.persist(path)

    raw = path.read_text(encoding="utf-8").replace("Observed", "Tampered")
    path.write_text(raw, encoding="utf-8")

    with pytest.raises(ValueError, match="memory-digest-invalid"):
        ProjectMemoryStore.load(path)


def test_chain_tampering_or_reordering_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "memory.jsonl"
    store = ProjectMemoryStore()
    first = ProjectMemory.create(
        project_id="p1", kind="decision", statement="First",
        status="authoritative", source="user",
    )
    store.append(first)
    second = ProjectMemory.create(
        project_id="p1", kind="decision", statement="Second",
        status="authoritative", source="user", parent_digest=store.head_digest,
    )
    store.append(second)
    store.persist(path)

    lines = path.read_text(encoding="utf-8").splitlines()
    path.write_text("\n".join(reversed(lines)) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="memory-chain-broken"):
        ProjectMemoryStore.load(path)


def test_mixed_projects_cannot_share_a_memory_store() -> None:
    first = ProjectMemory.create(
        project_id="p1", kind="decision", statement="First",
        status="authoritative", source="user",
    )
    second = ProjectMemory.create(
        project_id="p2", kind="decision", statement="Second",
        status="authoritative", source="user", parent_digest=first.digest,
    )
    with pytest.raises(ValueError, match="memory-store-project-mismatch"):
        ProjectMemoryStore((first, second))
