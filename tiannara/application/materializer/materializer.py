"""RepositoryMaterializer -- Phase 17.

Turns a successful ``ProjectCompilationReport`` into a materialized repository:

* writes each successful backend's ``CompilationResult`` files, namespaced by
  ``system_name`` (so a multi-backend fleet cannot collide);
* writes a lineage-complete ``provenance/manifest.json`` audit anchor;
* defaults to **deny** on failed verification: a bundle whose
  ``verification_report`` is present and not ``ok`` is refused unless
  ``force=True``. When forced, the override is recorded loudly in the manifest
  (``verification.forced=True``) -- never silent;
* drives source-control through the ``SourceControlBackend`` port. When no
  backend is supplied (e.g. git absent), it still produces the artifact tree
  + manifest without VCS steps.

This layer owns no intelligence and no codegen; it composes the Phase 16
report with the SourceControlBackend port.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tiannara.application.compiler.project_compiler import ProjectCompilationReport
from tiannara.application.compiler.writer import write_bundle
from tiannara.application.materializer.provenance_builder import build_manifest
from tiannara.domain.models.bundle import SystemDeploymentBundle
from tiannara.domain.models.compilation import CompilationResult
from tiannara.domain.ports.source_control import (
    CommitRef,
    SourceControlBackend,
    SourceControlError,
)

MANIFEST_RELATIVE_PATH = "provenance/manifest.json"


class MaterializationError(RuntimeError):
    """Raised when a repository cannot be materialized (e.g. unverified)."""


@dataclass(frozen=True)
class MaterializationResult:
    """Outcome of materializing a project into a source-control repository."""

    out_root: Path
    commit: CommitRef | None
    manifest_path: Path
    #: One SystemDeploymentBundle per successful outcome, so Phase 18's
    #: SoftwareFactory can feed ExecutionEnvironment.run_verification with the
    #: actual materialized bundle(s) instead of reconstructing them.
    bundles: tuple = ()


def _iter_files(root: Path) -> list[str]:
    return sorted(
        p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()
    )


def _verification_failed(outcome: Any) -> bool:
    report = outcome.verification_report
    return report is not None and not bool(report.ok)


class RepositoryMaterializer:
    """Materialize a compiled project into a source-control repository."""

    def __init__(self, sc_backend: SourceControlBackend | None) -> None:
        self._sc = sc_backend

    def materialize(
        self,
        report: ProjectCompilationReport,
        out_root: str | Path,
        *,
        force: bool = False,
        policy_name: str | None = None,
        build_id: str | None = None,
        commit_message: str = "materialize: compiled project bundle",
        branch: str = "main",
        author_name: str = "tiannara",
        author_email: str = "bot@tiannara.local",
    ) -> MaterializationResult:
        out_root = Path(out_root)
        out_root.mkdir(parents=True, exist_ok=True)

        successful: list[Any] = []
        bundles: list[SystemDeploymentBundle] = []
        for outcome in report.outcomes:
            if getattr(outcome, "status", None) != "success":
                continue
            result = getattr(outcome, "result", None)
            if not isinstance(result, CompilationResult):
                continue
            # Backends root their own files at <system_name>/ (e.g.
            # ``order-management/main.py``); writing to out_root preserves that
            # layout, which is what makes a multi-backend fleet collision-free
            # (distinct system names -> distinct top-level dirs).
            write_bundle(result, out_root)
            successful.append(outcome)
            bundles.append(
                SystemDeploymentBundle(
                    project_id=result.system_name,
                    backend_name=result.backend_id,
                    isr_hash=report.isr_hash,
                    path=out_root,
                    artifacts=sorted(result.files.keys()),
                    capability_manifest=result.capability_manifest,
                )
            )
        if not successful:
            raise MaterializationError(
                "no successful CompilationResult outcomes to materialize"
            )

        forced = False
        if any(_verification_failed(o) for o in successful):
            if not force:
                identities = ", ".join(
                    f"{o.result.backend_id}:{o.result.system_name}"
                    for o in successful
                    if _verification_failed(o)
                )
                raise MaterializationError(
                    f"verification failed for bundle(s) [{identities}]; "
                    "pass force=True to override"
                )
            forced = True

        if policy_name is None:
            policy_name = getattr(report, "policy_name", None)
        manifest = build_manifest(
            report=report,
            outcomes=successful,
            forced=forced,
            policy_name=policy_name,
            build_id=build_id,
        )
        manifest_path = out_root / MANIFEST_RELATIVE_PATH
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            manifest.model_dump_json(indent=2), encoding="utf-8"
        )

        commit: CommitRef | None = None
        if self._sc is not None:
            self._sc.init(str(out_root))
            self._sc.add(str(out_root), _iter_files(out_root))
            commit = self._sc.commit(
                str(out_root), commit_message, author_name, author_email
            )
            try:
                self._sc.branch(str(out_root), branch)
            except SourceControlError:
                pass
        return MaterializationResult(
            out_root=out_root,
            commit=commit,
            manifest_path=manifest_path,
            bundles=tuple(bundles),
        )
