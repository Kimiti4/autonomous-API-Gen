"""Concrete RepairProviders for Phase 18.

NullRepairProvider is the "no automatic repair" strategy (fail fast).
RematerializationRepairProvider is a deterministic, semantics-preserving
repair: it restores files missing from a bundle from the canonical
CompilationResult artifacts, addressing the ``missing_files`` failure class.

Deliberately NOT included: silent semantic patching (syntax/dep-direction
rewrites). Those are higher-risk and belong to specialised providers or,
preferably, ISR-level re-entry (tracked follow-up).
"""

from __future__ import annotations

from pathlib import Path

from tiannara.domain.ports.repair import RepairAction, RepairReport, RepairRequest


class NullRepairProvider:
    def diagnose(self, request: RepairRequest) -> tuple[RepairAction, ...]:
        return ()

    def apply(self, bundle_path: str, actions: tuple[RepairAction, ...]) -> RepairReport:
        return RepairReport(
            attempted=False,
            actions=(),
            applied=False,
            reason="no repair strategy configured",
        )


class RematerializationRepairProvider:
    """Restores missing files from the canonical source artifacts."""

    def diagnose(self, request: RepairRequest) -> tuple[RepairAction, ...]:
        static_report = request.static_report
        if static_report is None:
            return ()
        missing = list(getattr(static_report, "missing_files", None) or [])
        actions: list[RepairAction] = []
        for rel in missing:
            content = request.source_artifacts.get(rel)
            if content is not None:
                actions.append(
                    RepairAction(
                        operation="write_file",
                        target=rel,
                        content=content,
                        description=f"restore missing file {rel}",
                    )
                )
        return tuple(actions)

    def apply(self, bundle_path: str, actions: tuple[RepairAction, ...]) -> RepairReport:
        if not actions:
            return RepairReport(
                attempted=True, actions=(), applied=False, reason="no applicable actions"
            )
        root = Path(bundle_path)
        applied: list[RepairAction] = []
        for action in actions:
            if action.operation == "write_file" and action.content is not None:
                target = root / action.target
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(action.content, encoding="utf-8")
                applied.append(action)
        return RepairReport(
            attempted=True, actions=tuple(applied), applied=bool(applied)
        )
