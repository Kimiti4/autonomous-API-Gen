"""CampaignRunner — orchestrates CBC-1 trials and aggregates results."""
from __future__ import annotations
import hashlib
import json
import os
import tempfile
import uuid
from typing import Any

from compiler.core.plan import CompilationPlan
from compiler.core.conformance import CHECKER
from compiler.core.repository import GeneratedRepository, build_repository
from compiler.core.protocol import (
    BackendIdentity, eligible_for_behavioral_certification,
)
from certification.core.trial import (
    Trial,
    TrialStage,
    StageEvidence,
    compose_verdict,
)
from certification.core import metrics as M
from certification.provenance.bundle import ProvenanceBundle
from autonomous_api.app.engine.source_bound_full_stack import (
    SourceBoundSemanticCorrespondenceVerifier,
)


def _now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _h(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _run_independent_verifier(verifier: Any, candidate_dir: str,
                              plan_hash: str, plan_path: str) -> tuple[bool, str]:
    """Run the mandatory independent verifier; absence/errors never pass."""
    if verifier is None:
        return False, "verification unavailable: no independent verifier configured"
    try:
        result = verifier.verify(candidate_dir, plan_hash, plan_path)
    except Exception as exc:
        return False, f"verification failed closed: {type(exc).__name__}: {exc}"
    if result is not True:
        return False, f"verification did not return explicit True (result={result!r})"
    return True, "independent verification passed"


def _run_candidate_bound_full_stack_verifier(verifier: Any, inputs: Any, candidate_hash: str) -> tuple[bool, str]:
    """Require explicit full-stack IR inputs and a passing verifier result."""
    if verifier is None:
        return False, "full-stack verification unavailable: verifier not configured"
    if not isinstance(inputs, tuple) or len(inputs) != 5:
        return False, "full-stack verification unavailable: five explicit IR inputs required"
    if not candidate_hash:
        return False, "full-stack verification unavailable: candidate hash missing"
    # A digest in the log is not binding. The verifier must receive the
    # candidate digest as an input and echo it in its structured result.
    # Do not fall back to verify_full_stack(*inputs): that API checks IR
    # coherence but cannot attest which generated candidate the IR describes.
    verify_bound = getattr(verifier, "verify_bound", None)
    if not callable(verify_bound):
        return False, (
            "full-stack verification unavailable: verifier must implement "
            "verify_bound(inputs, candidate_hash)"
        )
    try:
        result = verify_bound(inputs, candidate_hash)
    except Exception as exc:
        return False, f"full-stack verification failed closed: {type(exc).__name__}: {exc}"
    if getattr(result, "passed", None) is not True:
        return False, f"full-stack verification did not pass; candidate_hash={candidate_hash}; findings={getattr(result, 'findings', None)!r}"
    if getattr(result, "candidate_hash", None) != candidate_hash:
        return False, (
            "full-stack verification candidate binding mismatch; "
            f"expected={candidate_hash}; received={getattr(result, 'candidate_hash', None)!r}"
        )
    return True, f"full-stack verification passed with matching candidate binding; candidate_hash={candidate_hash}"


def _run_semantic_correspondence_verifier(
    verifier: Any, inputs: Any, candidate_hash: str,
) -> tuple[dict[str, Any], str]:
    """Run a source-to-mapping-to-candidate verifier; never infer semantic proof."""
    if verifier is None:
        return {}, "semantic correspondence unavailable: verifier not configured"
    if inputs is None:
        return {}, "semantic correspondence unavailable: source and mapping inputs missing"
    if not candidate_hash:
        return {}, "semantic correspondence unavailable: candidate hash missing"
    verify = getattr(verifier, "verify_bound", None)
    if not callable(verify):
        return {}, "semantic correspondence unavailable: verifier must implement verify_bound(inputs, candidate_hash)"
    try:
        result = verify(inputs, candidate_hash)
    except Exception as exc:
        return {}, f"semantic correspondence failed closed: {type(exc).__name__}: {exc}"
    evidence = {
        "passed": getattr(result, "passed", None) is True,
        "source_hash": getattr(result, "source_hash", ""),
        "mapping_hash": getattr(result, "mapping_hash", ""),
        "candidate_hash": getattr(result, "candidate_hash", ""),
    }
    if evidence["passed"] is not True:
        return evidence, f"semantic correspondence did not pass: {getattr(result, 'findings', None)!r}"
    for key in ("source_hash", "mapping_hash", "candidate_hash"):
        if not isinstance(evidence[key], str) or not evidence[key].strip():
            evidence["passed"] = False
            return evidence, f"semantic correspondence missing {key}"
    if evidence["candidate_hash"] != candidate_hash:
        evidence["passed"] = False
        return evidence, "semantic correspondence candidate binding mismatch"
    return evidence, "semantic correspondence passed with matching candidate binding"


def _unconfigured_stage(stage: TrialStage) -> tuple[bool, str]:
    """A missing execution adapter is absence of evidence, never a pass."""
    return False, f"not_configured: no real {stage.value} stage adapter supplied"


class CampaignRunner:
    """Orchestrates a single CBC-1 trial: compile → stage pipeline → evidence → verdict.

    Execution adapters are injected. Missing build, test, deploy, runtime,
    destroy, or independent-verification adapters are hard failures.
    """

    def __init__(
        self,
        builder: Any = None,
        tester: Any = None,
        deployer: Any = None,
        prober: Any = None,
        destroyer: Any = None,
        verifier: Any = None,
        full_stack_verifier: Any = None,
        semantic_correspondence_verifier: Any = None,
    ) -> None:
        self.builder = builder
        self.tester = tester
        self.deployer = deployer
        self.prober = prober
        self.destroyer = destroyer
        self.verifier = verifier
        self.full_stack_verifier = full_stack_verifier
        # Use the production verifier by default. Missing source/mapping inputs
        # still fail closed in the verifier; no evidence is synthesized.
        self.semantic_correspondence_verifier = (
            semantic_correspondence_verifier or SourceBoundSemanticCorrespondenceVerifier()
        )

    def run_trial(
        self,
        intent: str,
        category: str,
        novelty_class: str,
        plan: CompilationPlan,
        revision_id: str,
        backend: Any,
        backend_test_cmd: list[str] | None = None,
        corpus_hash: str = "",
        requirement_graph_hash: str = "",
        genome_hash: str = "",
        workload: Any = None,
        artifacts: Any = None,
        full_stack_inputs: tuple[Any, Any, Any, Any, Any] | None = None,
        semantic_correspondence_inputs: Any = None,
    ) -> Trial:
        trial_id = str(uuid.uuid4())
        ident: BackendIdentity = backend.identity()

        evidence: list[StageEvidence] = []
        stage_results: dict[TrialStage, bool] = {}

        def _record(stage: TrialStage, passed: bool, detail: str = "") -> None:
            stage_results[stage] = passed
            evidence.append(StageEvidence(
                stage=stage,
                passed=passed,
                started_at=_now(),
                completed_at=_now(),
                logs_hash=_h(detail),
                detail=detail,
            ))

        repo = backend.compile(plan)

        d = tempfile.mkdtemp(prefix="cbc1-")
        for p, c in repo.files.items():
            full = os.path.join(d, p)
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w", encoding="utf-8") as f:
                f.write(c)

        repo_hash_for_gate = _h(json.dumps(sorted(repo.files.items()), separators=(",", ":"), ensure_ascii=False))
        ir_snapshot = ""
        if isinstance(full_stack_inputs, tuple) and len(full_stack_inputs) == 5:
            try:
                ir_snapshot = json.dumps(
                    [item.to_dict() if hasattr(item, "to_dict") else repr(item)
                     for item in full_stack_inputs],
                    sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                )
            except Exception:
                ir_snapshot = ""
        candidate_hash = _h(repo_hash_for_gate + "\n" + ir_snapshot) if ir_snapshot else ""

        if not eligible_for_behavioral_certification(ident):
            _record(TrialStage.STRUCTURAL, False,
                    f"backend_class={ident.backend_class.value} below behavioral bar")
            _record(TrialStage.SEMANTIC, False,
                    f"backend_class={ident.backend_class.value} below behavioral bar")
            for s in (TrialStage.BUILD, TrialStage.TEST, TrialStage.DEPLOY,
                      TrialStage.RUNTIME, TrialStage.DESTROY, TrialStage.VERIFY):
                _record(s, False, "skipped: not eligible")
            verdict = "NOT_CERTIFIED"
        else:
            conf = backend.conformance(plan, repo)
            _record(TrialStage.STRUCTURAL, conf.passed, f"missing={conf.missing}")
            _record(TrialStage.SEMANTIC, conf.passed, f"semantic={conf.passed}")

            if self.builder:
                tag = f"cbc1-{trial_id[:8]}"
                b_ok, b_hash = self.builder.build(d, tag)
                _record(TrialStage.BUILD, b_ok, f"build_hash={b_hash}")
            else:
                ok, detail = _unconfigured_stage(TrialStage.BUILD)
                _record(TrialStage.BUILD, ok, detail)

            if self.tester and backend_test_cmd:
                image = f"cbc1-{trial_id[:8]}"
                t_ok, t_hash = self.tester.run_tests(image, backend_test_cmd)
                _record(TrialStage.TEST, t_ok, f"test_hash={t_hash}")
            else:
                ok, detail = _unconfigured_stage(TrialStage.TEST)
                _record(TrialStage.TEST, ok, detail)

            cid = ""
            if self.deployer:
                d_ok, cid = self.deployer.deploy(f"cbc1-{trial_id[:8]}", 8000 + hash(trial_id) % 1000)
                _record(TrialStage.DEPLOY, d_ok, f"cid={cid}")
            else:
                ok, detail = _unconfigured_stage(TrialStage.DEPLOY)
                _record(TrialStage.DEPLOY, ok, detail)

            if self.prober:
                port = 8000 + hash(trial_id) % 1000
                r_ok = self.prober.probe(port)
                _record(TrialStage.RUNTIME, r_ok, f"runtime_ok={r_ok}")
            else:
                ok, detail = _unconfigured_stage(TrialStage.RUNTIME)
                _record(TrialStage.RUNTIME, ok, detail)

            if self.destroyer and cid:
                x_ok = self.destroyer.destroy(cid)
                _record(TrialStage.DESTROY, x_ok, f"destroy_ok={x_ok}")
            else:
                ok, detail = _unconfigured_stage(TrialStage.DESTROY)
                _record(TrialStage.DESTROY, ok, detail)

            plan_hash = hashlib.sha256(
                json.dumps(sorted(backend.element_paths(plan).values())).encode("utf-8")
            ).hexdigest()
            plan_path = os.path.join(d, ".plan.json")
            with open(plan_path, "w", encoding="utf-8") as fp:
                json.dump({"expected_paths": list(backend.element_paths(plan).values()),
                           "candidate_hash": candidate_hash}, fp)
            independent_ok, independent_detail = _run_independent_verifier(
                self.verifier, d, plan_hash, plan_path
            )
            full_stack_ok, full_stack_detail = _run_candidate_bound_full_stack_verifier(
                self.full_stack_verifier, full_stack_inputs, candidate_hash
            )
            # Campaign A supplies authoritative PlanArtifacts. Build the
            # verifier input from those real artifacts and the exact repository
            # returned by this backend; never infer the missing architecture map.
            if semantic_correspondence_inputs is None and artifacts is not None:
                try:
                    from autonomous_api.app.engine.source_bound_full_stack import (
                        source_snapshot_from_plan_artifacts,
                    )
                    semantic_correspondence_inputs = {
                        "source_artifacts": source_snapshot_from_plan_artifacts(artifacts),
                        "explicit_mapping": getattr(artifacts, "explicit_mapping", None),
                        "candidate_files": dict(repo.files),
                    }
                except Exception as exc:
                    semantic_correspondence_inputs = None
                    semantic_input_error = (
                        f"Campaign A source snapshot construction failed closed: "
                        f"{type(exc).__name__}: {exc}"
                    )
                else:
                    semantic_input_error = ""
            else:
                semantic_input_error = ""

            semantic_evidence, semantic_detail = _run_semantic_correspondence_verifier(
                self.semantic_correspondence_verifier,
                semantic_correspondence_inputs,
                repo.content_hash,
            )
            if semantic_input_error:
                semantic_evidence = {}
                semantic_detail = semantic_input_error
            verify_ok = independent_ok and full_stack_ok and semantic_evidence.get("passed") is True
            _record(
                TrialStage.VERIFY, verify_ok,
                f"independent=[{independent_detail}]; full_stack=[{full_stack_detail}]; "
                f"semantic_correspondence=[{semantic_detail}]",
            )

            verdict = compose_verdict(stage_results, evidence_present=True)

        metrics = M.compute(
            repo_files_count=len(repo.files),
            stages=stage_results,
            structural_passed=stage_results.get(TrialStage.STRUCTURAL, False),
            test_passed=stage_results.get(TrialStage.TEST, False),
            runtime_passed=stage_results.get(TrialStage.RUNTIME, False),
            repo_content_hash=repo.content_hash,
            files=repo.files,
            stage_evidence=evidence,
        )

        trial = Trial(
            trial_id=trial_id,
            intent=intent,
            category=category,
            novelty_class=novelty_class,
            requirement_graph_hash=requirement_graph_hash,
            genome_hash=genome_hash,
            isr_revision_id=revision_id,
            backend=ident.name,
            backend_class=ident.backend_class.value,
            backend_version=ident.version,
            compiler_version="1.4.0",
            repo_hash=repo.content_hash,
            corpus_hash=corpus_hash,
            stages=evidence,
            metrics=metrics,
            verdict=verdict,
            semantic_correspondence=semantic_evidence if 'semantic_evidence' in locals() else {},
        )

        if artifacts and workload is not None:
            conformance = backend.conformance(plan, repo)
            bundle = ProvenanceBundle.emit(
                trial=trial, plan=artifacts.plan, revision=artifacts.revision,
                genome=artifacts.genome, requirement_graph=artifacts.requirement_graph,
                backend_identity=ident, conformance=conformance,
            )
            bhash = ProvenanceBundle.bundle_hash(bundle)
            trial = trial.model_copy(update={"bundle_hash": bhash})
            for p, c in {**repo.files, **bundle}.items():
                full = os.path.join(d, p)
                os.makedirs(os.path.dirname(full), exist_ok=True)
                with open(full, "w", encoding="utf-8") as fp:
                    fp.write(c)

        return trial


class CampaignAggregator:
    """Aggregates trial results into success matrices and failure taxonomies."""

    def __init__(self) -> None:
        self.trials: list[Trial] = []

    def add(self, trial: Trial) -> None:
        self.trials.append(trial)

    def success_matrix(self) -> dict[str, dict[str, int]]:
        matrix: dict[str, dict[str, int]] = {}
        for t in self.trials:
            cat = t.category
            nc = t.novelty_class
            matrix.setdefault(cat, {}).setdefault(nc, 0)
            if t.verdict == "CERTIFIED":
                matrix[cat][nc] += 1
        return matrix

    def failure_taxonomy(self) -> dict[str, int]:
        taxonomy: dict[str, int] = {}
        for t in self.trials:
            if t.verdict != "CERTIFIED":
                for se in t.stages:
                    if not se.passed:
                        taxonomy[se.stage.value] = taxonomy.get(se.stage.value, 0) + 1
        return taxonomy

    def summary(self) -> dict[str, Any]:
        total = len(self.trials)
        certified = sum(1 for t in self.trials if t.verdict == "CERTIFIED")
        return {
            "total": total,
            "certified": certified,
            "not_certified": total - certified,
            "success_rate": certified / total if total else 0.0,
            "success_matrix": self.success_matrix(),
            "failure_taxonomy": self.failure_taxonomy(),
        }
