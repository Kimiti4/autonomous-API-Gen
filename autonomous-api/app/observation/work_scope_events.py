"""Governed emission of work-scope declarations into the Observatory stream."""

from __future__ import annotations

from app.engine.generation_scope import GenerationScope, validate_scope
from app.engine.project_scope import ChangeKind, ProjectIntent, ProjectScope, validate_project_scope
from app.observation.contracts.work_scope import WorkScopeDeclared
from app.observation.gateway.dispatcher import EventDispatcher


async def emit_work_scope_declared(
    dispatcher: EventDispatcher,
    *,
    stream_id: str,
    project_intent: str,
    project_kind: str,
    generation_scope: str,
    correlation_id: str,
    generation: int,
    causation_id: str | None = None,
):
    project = validate_project_scope(
        ProjectScope(ProjectIntent(project_intent), ChangeKind(project_kind))
    )
    scope = validate_scope(GenerationScope(generation_scope))
    surfaces = ("frontend", "backend", "api_contract")
    payload = WorkScopeDeclared(
        projectIntent=project.intent.value,
        projectKind=project.change_kind.value,
        generationScope=scope.scope.value,
        allowedSurfaces=[s for s in surfaces if scope.allows(s)],
        preservedSurfaces=[s for s in surfaces if not scope.allows(s)],
    )
    return await dispatcher.emit(
        stream_id=stream_id,
        event_type="scope.declared",
        payload=payload,
        correlation_id=correlation_id,
        generation=generation,
        causation_id=causation_id,
    )
