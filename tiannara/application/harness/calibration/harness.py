"""Phase-31 BackendCalibrationHarness — compiler-correctness calibration slice.

Composites Phase-19 primitives (no duplication):
    SystemModel -> derive_compilation_requirements -> plan_compilation_across_backends
        -> backend.generate -> write_bundle (per-backend dir) -> backend.build_profile
            -> make_verifier -> verify (static) -> optional runtime (toolchain-gated)
        -> CertificationEvidence -> EvidenceLedger

Distinct from the full ``StratifiedCalibrationHarness`` (Intent -> Evolution ->
single target backend). This harness measures *first-pass backend correctness*
across *every* registered backend for an ISR corpus -- the compiler-certification
gate, with repair deliberately excluded (a Phase-18 factory concern).
"""
from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

from tiannara.application.compiler.build_profile import (
    BackendBuildProfile,
    make_verifier,
)
from tiannara.application.compiler.composition import build_compiler_registry
from tiannara.application.compiler.derivation import derive_compilation_requirements
from tiannara.application.compiler.naming import slugify
from tiannara.application.compiler.selector import (
    DEFAULT_SELECTION_POLICY,
    plan_compilation_across_backends,
)
from tiannara.application.compiler.writer import write_bundle
from tiannara.application.harness.calibration.corpus import DEFAULT_CORPUS, as_models
from tiannara.application.harness.calibration.report import (
    CalibrationOutcome,
    CalibrationReport,
)
from tiannara.domain.models.bundle import SystemDeploymentBundle
from tiannara.domain.models.evidence import CertificationEvidence, FitnessVector, Verdict
from tiannara.domain.models.system_model import SystemModel
from tiannara.infrastructure.sandbox.local_environment import LocalExecutionEnvironment
from tiannara.infrastructure.sandbox.docker_environment import DockerExecutionEnvironment

GATE_SEMANTICS = (
    "successful generation = static-verification pass (go.mod/well-formedness + "
    "required files + inward-import direction); runtime-verify is additional "
    "evidence, RUN only when the backend's own toolchain is present on PATH, "
    "otherwise 'skipped:toolchain_absent' (pass-with-evidence and recorded). "
    "Repair is not applied in this calibration slice."
)


def build_calibration_registry():
    """Registry containing every backend the harness should certify."""
    reg = build_compiler_registry()  # FastAPI (default production)
    from tiannara.application.compiler.go_hexagonal_backend import GoHexagonalBackend

    go = GoHexagonalBackend()
    reg.register(go, go.build_profile_declaration())
    return reg


class BackendCalibrationHarness:
    """Run the same ISR corpus against every registered backend."""

    def __init__(
        self,
        registry,
        ledger,
        policy=DEFAULT_SELECTION_POLICY,
    ) -> None:
        self._registry = registry
        self._ledger = ledger
        self._policy = policy

    def calibrate(
        self,
        corpus=None,
        out_root: str | Path = "calibration-out",
    ) -> CalibrationReport:
        models = as_models(corpus)
        out_root = Path(out_root)
        outcomes: list[CalibrationOutcome] = []
        backends_tested: set[str] = set()

        for model in models:
            isr_hash = model.content_hash()
            slug = slugify(model.system_name)
            requirements = derive_compilation_requirements(model)
            if not requirements:
                # No backend-service requirement for this model; nothing to certify.
                continue
            plan = plan_compilation_across_backends(
                self._registry, requirements, self._policy
            )
            for planned in plan.planned:
                backend = self._registry.backend(planned.backend_id)
                outcome = self._evaluate(model, slug, isr_hash, planned, backend, out_root)
                outcomes.append(outcome)
                backends_tested.add(planned.backend_id)

        total = len(outcomes)
        passed = sum(1 for o in outcomes if o.ok)
        ran = sum(1 for o in outcomes if o.runtime_status.startswith("ran"))
        return CalibrationReport(
            corpus_size=len(models),
            backends_tested=tuple(sorted(backends_tested)),
            outcomes=tuple(outcomes),
            success_rate=(passed / total) if total else 0.0,
            runtime_coverage=(ran / total) if total else 0.0,
            gate_semantics=GATE_SEMANTICS,
            ledger_path=str(getattr(self._ledger, "_path", "")),
        )

    # -- internals ---------------------------------------------------------

    def _evaluate(self, model, slug, isr_hash, planned, backend, out_root) -> CalibrationOutcome:
        backend_id = planned.backend_id
        try:
            result = backend.generate(model)
        except Exception as exc:  # noqa: BLE001 -- collect, don't crash the matrix
            evidence = self._record_evidence(
                slug, isr_hash, backend_id, ok=False, error=f"{type(exc).__name__}: {exc}"
            )
            return CalibrationOutcome(
                system_name=slug,
                isr_hash=isr_hash,
                backend_id=backend_id,
                bundle_path=None,
                verification_report=None,
                runtime_status="skipped:no_test_command",
                test_run=None,
                ok=False,
                evidence=evidence,
            )

        bundle_dir = out_root / backend_id
        bundle_dir.mkdir(parents=True, exist_ok=True)
        write_bundle(result, bundle_dir)

        profile: BackendBuildProfile = backend.build_profile(slug)
        verifier = make_verifier(
            profile.language,
            package=slug,
            required_files=list(profile.required_files),
        )
        verification_report = verifier.verify(bundle_dir)

        runtime_status, test_run = self._run_runtime(profile, backend_id, slug, bundle_dir, result)

        static_ok = bool(verification_report.ok)
        runtime_ok = (
            bool(getattr(test_run, "passed", True))
            if runtime_status.startswith("ran")
            else True
        )
        ok = static_ok and runtime_ok

        evidence = self._record_evidence(
            slug, isr_hash, backend_id, ok=ok, test_run=test_run,
            error=None if ok else verification_report_error(verification_report),
            fitness_metrics={
                "static": 1.0 if static_ok else 0.0,
                "runtime": 1.0 if runtime_ok else 0.0,
            },
        )

        bundle = SystemDeploymentBundle(
            project_id=slug,
            backend_name=backend_id,
            isr_hash=isr_hash,
            path=bundle_dir,
            artifacts=sorted(result.files.keys()),
            capability_manifest=result.capability_manifest,
        )
        return CalibrationOutcome(
            system_name=slug,
            isr_hash=isr_hash,
            backend_id=backend_id,
            bundle_path=bundle_dir,
            verification_report=verification_report,
            runtime_status=runtime_status,
            test_run=test_run,
            ok=ok,
            evidence=evidence,
        )

    def _run_runtime(self, profile, backend_id, slug, bundle_dir, result):
        if not profile.test_command:
            return "skipped:no_test_command", None
        # Docker-first: a backend that declares a runtime_image runs its
        # test_command inside the image (toolchain contained in the container,
        # not required on the host). Falls back to local execution when Docker
        # is absent, and to an honest skip when neither is usable.
        if profile.runtime_image and DockerExecutionEnvironment.available():
            env = DockerExecutionEnvironment(
                test_command=profile.test_command,
                runtime_image=profile.runtime_image,
                build_command=profile.build_command if profile.requires_build_phase else None,
            )
        else:
            tool = profile.test_command[0]
            if not shutil.which(tool):
                return "skipped:toolchain_absent", None
            env = LocalExecutionEnvironment(
                profile.test_command,
                build_command=profile.build_command if profile.requires_build_phase else None,
            )
        bundle = SystemDeploymentBundle(
            project_id=slug,
            backend_name=backend_id,
            isr_hash="",
            path=bundle_dir,
            artifacts=sorted(result.files.keys()),
            capability_manifest=result.capability_manifest,
        )
        try:
            coro = env.run_verification(bundle)
            test_run = asyncio.run(coro) if asyncio.iscoroutine(coro) else coro
        except Exception:  # noqa: BLE001 -- record runtime failures, don't crash matrix
            return "skipped:runtime_error", None
        return "ran", test_run

    def _record_evidence(
        self, slug, isr_hash, backend_id, ok, test_run=None, error=None,
        fitness_metrics=None,
    ) -> CertificationEvidence:
        evidence = CertificationEvidence(
            project_id=slug,
            isr_hash=isr_hash,
            genome_id=f"pre-evolution:{isr_hash[:16]}",
            backend_name=backend_id,
            compilation_success=ok,
            test_run=test_run,
            fitness=FitnessVector(metrics=fitness_metrics or {}),
            verdict=Verdict.PASS if ok else Verdict.FAIL,
            error=error,
        )
        return self._ledger.append(evidence)


def verification_report_error(report) -> str | None:
    """Summarize a failed verification report as the evidence error field."""
    if report is None or report.ok:
        return None
    parts = []
    if report.missing_files:
        parts.append(f"missing: {report.missing_files}")
    if report.syntax_errors:
        parts.append(f"syntax: {report.syntax_errors}")
    if report.dependency_violations:
        parts.append(f"deps: {report.dependency_violations}")
    return "; ".join(parts) if parts else "verification failed"
