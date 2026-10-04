import pytest
from app.core.contracts.events import EventSource
from app.observation.gateway.dispatcher import EventDispatcher
from app.observation.sequences.memory import InMemorySequenceStore
from app.observation.work_scope_events import emit_work_scope_declared


@pytest.mark.asyncio
async def test_work_scope_declaration_is_persisted_and_ordered():
    store = InMemorySequenceStore()
    dispatcher = EventDispatcher(
        store=store,
        source=EventSource(subsystem="evolution-engine", revision="test"),
    )
    event = await emit_work_scope_declared(
        dispatcher,
        stream_id="project-1",
        project_intent="improve",
        project_kind="existing_project",
        generation_scope="frontend_only",
        correlation_id="corr-1",
        generation=1,
    )
    assert event.eventType == "scope.declared"
    assert event.sequence == 0
    replayed = await store.replay("project-1", -1, 10)
    assert len(replayed) == 1
    assert replayed[0].payload.generationScope == "frontend_only"


@pytest.mark.asyncio
async def test_invalid_scope_is_rejected_before_persistence():
    store = InMemorySequenceStore()
    dispatcher = EventDispatcher(
        store=store,
        source=EventSource(subsystem="evolution-engine", revision="test"),
    )
    with pytest.raises(ValueError):
        await emit_work_scope_declared(
            dispatcher,
            stream_id="project-1",
            project_intent="create",
            project_kind="existing_project",
            generation_scope="frontend_only",
            correlation_id="corr-1",
            generation=1,
        )
    assert await store.current("project-1") == -1
