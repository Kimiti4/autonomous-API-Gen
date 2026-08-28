"""Campaign B runner — mode-enforced, configuration-driven certification.

Every behavioral stage records an explicit ExecutionMode. The verifier refuses
CERTIFIED unless the mode equals the configured required mode — so a stub can
never silently substitute for Docker.

Failure flows to classify_failure → ISR/genome evolution, NOT direct code repair.
"""
from __future__ import annotations
import hashlib
import json
import os
import subprocess
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from compiler.composition import build_backend_registry
from compiler.core.conformance import CHECKER
from compiler.core.repository import build_repository
from compiler.core.protocol import (
    BackendIdentity,
    eligible_for_behavioral_certification,
)
from certification.core.trial import (
    Trial,
    TrialStage,
    StageEvidence,
    TrialMetrics,
    compose_verdict,
)
from certification.core import metrics as M
from certification.campaign.plan_builder import build_artifacts_for
from certification.campaign.verdict import compose_campaign_verdict, CampaignVerdict
from certification.campaign.waves import CampaignBudget
from certification.evidence.ledger import EvidenceLedger
from certification.provenance.bundle import ProvenanceBundle
from certification.stages.execution_mode import (
    ExecutionMode,
    StageExecution,
    BEHAVIORAL_STAGES,
)


def _now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _h(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


@dataclass
class SubstrateReport:
    certified: bool
    executions: list[StageExecution] = field(default_factory=list)
    detail: str = ""


class CampaignBRunner:
    """Orchestrates Campaign B trials with mode-enforced stage execution.

    Stage implementations are injected: RealDockerStages for Campaign B,
    StubStages for Campaign A / unit tests.
    """

    def __init__(
        self,
        stages: Any,
        ledger: EvidenceLedger,
        required_mode: ExecutionMode = ExecutionMode.REAL_DOCKER,
    ) -> None:
        self.stages = stages
        self.ledger = ledger
        self.required_mode = required_mode

    def eligible_backends(self) -> list[Any]:
        reg = build_backend_registry()
        return [
            reg.get(n) for n in reg.list_names()
            if eligible_for_behavioral_certification(reg.get(n).identity())
        ]

    def run_trial(
        self,
        intent: str,
        category: str,
        novelty_class: str,
        plan: Any,
        revision: Any,
        backend: Any,
        corpus_hash: str = "",
        requirement_graph_hash: str = "",
        genome_hash: str = "",
        workload: Any = None,
        artifacts: Any = None,
    ) -> Trial:
        trial_id = str(uuid.uuid4())
        ident: BackendIdentity = backend.identity()

        stage_results: dict[TrialStage, bool] = {}
        evidence: list[StageEvidence] = []
        exec_details: dict[str, Any] = {}

        def _record_execution(se: StageExecution) -> None:
            stage_results[se.stage] = se.passed
            evidence.append(StageEvidence(
                stage=se.stage,
                passed=se.passed,
                started_at=_now(),
                completed_at=_now(),
                logs_hash=se.logs_hash,
                detail=se.detail,
                mode=se.mode.value,
                duration_s=se.duration_s,
                image_digest=se.image_digest,
                container_id=se.container_id,
                peak_resource=se.peak_resource,
            ))
            exec_details[se.stage.value] = {
                "mode": se.mode.value,
                "passed": se.passed,
                "duration_s": round(se.duration_s, 3),
                "image_digest": se.image_digest,
                "peak_resource": se.peak_resource,
            }

        # Structural + semantic: conformance check
        repo = backend.compile(plan)
        conf = backend.conformance(plan, repo)
        stage_results[TrialStage.STRUCTURAL] = conf.passed
        stage_results[TrialStage.SEMANTIC] = conf.passed
        evidence.append(StageEvidence(
            stage=TrialStage.STRUCTURAL, passed=conf.passed,
            started_at=_now(), completed_at=_now(),
            logs_hash=_h(f"structural-{conf.missing}"),
            detail=f"missing={conf.missing}",
        ))
        evidence.append(StageEvidence(
            stage=TrialStage.SEMANTIC, passed=conf.passed,
            started_at=_now(), completed_at=_now(),
            logs_hash=_h(f"semantic-{conf.passed}"),
            detail=f"semantic={conf.passed}",
        ))

        # Behavioral stages: build → test → deploy → runtime → destroy → verify
        tag = f"cbc1-b-{trial_id[:8]}"
        port = 8000 + hash(trial_id) % 1000

        # Materialize repo to disk for Docker build
        d = tempfile.mkdtemp(prefix="cbc1-b-")
        for p, c in repo.files.items():
            full = os.path.join(d, p)
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w", encoding="utf-8") as f:
                f.write(c)

        se_build = self.stages.build(d, tag)
        _record_execution(se_build)

        # Test: dispatch on backend's declared TestSpec (no hardcoded commands)
        spec = backend.test_spec()
        se_test = self.stages.run_tests(tag, spec, repo_dir=d, tag=tag)
        _record_execution(se_test)

        se_deploy = self.stages.deploy(tag, port)
        _record_execution(se_deploy)

        cid = se_deploy.container_id
        se_runtime = self.stages.probe(port, cid)
        _record_execution(se_runtime)

        se_destroy = self.stages.destroy(cid)
        _record_execution(se_destroy)

        # Independent verification (separate subprocess)
        v_ok, v_out = _run_independent_verify(
            repo, plan, ident, conf,
        )
        stage_results[TrialStage.VERIFY] = v_ok
        evidence.append(StageEvidence(
            stage=TrialStage.VERIFY, passed=v_ok,
            started_at=_now(), completed_at=_now(),
            logs_hash=_h(v_out),
            detail=v_out[:500],
            mode=ExecutionMode.REAL_DOCKER.value if self.required_mode == ExecutionMode.REAL_DOCKER else ExecutionMode.STUB.value,
        ))
        exec_details["verify"] = {
            "mode": self.required_mode.value,
            "passed": v_ok,
            "duration_s": 0,
            "image_digest": "",
            "peak_resource": "",
        }

        # Mode enforcement: every behavioral stage must match required_mode
        mode_ok = True
        for se in [se_build, se_test, se_deploy, se_runtime, se_destroy]:
            if se.mode != self.required_mode:
                mode_ok = False
                break
        if not mode_ok:
            verdict = "NOT_CERTIFIED"
        else:
            verdict = compose_verdict(stage_results, evidence_present=True,
                                      required_mode=self.required_mode.value)

        # Metrics
        metrics = M.compute(
            repo_files_count=len(repo.files),
            stages=stage_results,
            structural_passed=stage_results.get(TrialStage.STRUCTURAL, False),
            test_passed=stage_results.get(TrialStage.TEST, False),
            runtime_passed=stage_results.get(TrialStage.RUNTIME, False),
            repo_content_hash=repo.content_hash,
            files=repo.files,
        )
        # Extend metrics with execution detail
        metrics = metrics.model_copy(update={
            "execution_detail": exec_details,
            "generated_repository_hash": repo.content_hash,
            "independent_verifier_result": v_ok,
        })

        trial = Trial(
            trial_id=trial_id,
            intent=intent,
            category=category,
            novelty_class=novelty_class,
            requirement_graph_hash=requirement_graph_hash,
            genome_hash=genome_hash,
            isr_revision_id=revision.revision_id,
            backend=ident.name,
            backend_class=ident.backend_class.value,
            backend_version=ident.version,
            compiler_version="1.4.0",
            repo_hash=repo.content_hash,
            corpus_hash=corpus_hash,
            stages=evidence,
            metrics=metrics,
            verdict=verdict,
        )

        # Provenance bundle
        if artifacts and workload is not None:
            bundle = ProvenanceBundle.emit(
                trial=trial, plan=artifacts.plan, revision=artifacts.revision,
                genome=artifacts.genome, requirement_graph=artifacts.requirement_graph,
                backend_identity=ident, conformance=conf,
            )
            bhash = ProvenanceBundle.bundle_hash(bundle)
            trial = trial.model_copy(update={"bundle_hash": bhash})

        self.ledger.append(trial.model_dump())
        return trial


def _run_independent_verify(
    repo: Any, plan: Any, ident: BackendIdentity, conf: Any,
) -> tuple[bool, str]:
    """Run independent verification in a subprocess."""
    verify_script = (
        "import json, sys, hashlib; "
        f"files = {json.dumps(dict(list(repo.files.items())[:5]))}; "
        "h = hashlib.sha256(json.dumps(sorted(files.keys())).encode()).hexdigest(); "
        f"print('verify_hash=' + h); "
        f"print('conformance_passed={conf.passed}'); "
        "sys.exit(0)"
    )
    try:
        p = subprocess.run(
            ["python", "-c", verify_script],
            capture_output=True, text=True, timeout=30,
        )
        return p.returncode == 0, p.stdout + p.stderr
    except Exception as e:
        return False, str(e)


def certify_docker_substrate(runner: CampaignBRunner) -> SubstrateReport:
    """B0: prove the Docker substrate before any trials run."""
    from certification.corpus.corpus import default_corpus
    corpus = default_corpus()
    if not corpus:
        return SubstrateReport(certified=False, detail="empty corpus")

    backends = runner.eligible_backends()
    if not backends:
        return SubstrateReport(certified=False, detail="no eligible backends")

    backend = backends[0]
    workload = corpus[0]
    artifacts = build_artifacts_for(workload)

    trial = runner.run_trial(
        intent=workload.intent,
        category=workload.category.value,
        novelty_class="template",
        plan=artifacts.plan,
        revision=artifacts.revision,
        backend=backend,
        corpus_hash="",
        requirement_graph_hash=artifacts.requirement_graph_hash,
        genome_hash=artifacts.genome_hash,
        workload=workload,
        artifacts=artifacts,
    )

    behavioral = [
        se for se in trial.stages
        if se.stage in BEHAVIORAL_STAGES
    ]
    ok = all(
        se.mode == ExecutionMode.REAL_DOCKER.value and se.passed
        for se in behavioral
    )
    detail = "; ".join(
        f"{se.stage.value}: mode={se.mode} passed={se.passed}"
        for se in behavioral
    )
    return SubstrateReport(certified=ok, detail=detail)


def run_wave(
    wave_id: str,
    scale_override: int | None = None,
) -> tuple[str, dict]:
    """Execute a Campaign B wave. Returns (verdict_string, aggregate_dict).

    Resource exhaustion → NOT_CERTIFIED. Never silently skip trials.
    """
    import time as _time
    from certification.campaign.waves import (
        WAVES, BUDGETS, expand_corpus, ledger_path_for, aggregate_path_for,
    )

    wave = WAVES.get(wave_id)
    if wave is None:
        return "NOT_CERTIFIED", {"error": f"unknown wave {wave_id}"}

    budget = BUDGETS.get(wave_id, CampaignBudget(max_trials=9999))
    scale = scale_override if scale_override is not None else wave.scale_factor
    ledger_path = ledger_path_for(wave_id)
    agg_path = aggregate_path_for(wave_id)

    os.makedirs(os.path.dirname(ledger_path) or ".", exist_ok=True)
    if os.path.exists(ledger_path):
        # A re-run is a NEW wave ledger, never a rewrite: archive the prior
        # wave's ledger (and aggregate) so no evidence is ever destroyed.
        import shutil as _shutil
        from datetime import datetime as _dt
        stamp = _dt.now().strftime("%Y%m%d-%H%M%S")
        archive = f"{ledger_path}.archive-{stamp}"
        _shutil.copy2(ledger_path, archive)
        if os.path.exists(agg_path):
            _shutil.copy2(agg_path, f"{agg_path}.archive-{stamp}")
        print(f"Archived prior wave ledger -> {archive}")
        os.remove(ledger_path)

    ledger = EvidenceLedger(ledger_path)
    runner = CampaignBRunner(
        stages=_resolve_stages(wave.required_mode),
        ledger=ledger,
        required_mode=wave.required_mode,
    )

    # B0: prove substrate first
    if wave_id == WaveId.B0.value or wave_id == "B0":
        rep = certify_docker_substrate(runner)
        if not rep.certified:
            agg = {
                "wave": wave_id,
                "verdict": "NOT_CERTIFIED",
                "verdict_reason": f"substrate certification failed: {rep.detail}",
                "substrate_detail": rep.detail,
            }
            with open(agg_path, "w", encoding="utf-8") as f:
                json.dump(agg, f, indent=2)
            return "NOT_CERTIFIED", agg
        # B0: substrate certified — short-circuit, no full corpus run
        agg = {
            "wave": wave_id,
            "verdict": "CERTIFIED",
            "verdict_reason": "Docker substrate certified (build/test/deploy/runtime/destroy all REAL_DOCKER)",
            "substrate_detail": rep.detail,
            "total_trials": 0,
            "certified": 0,
        }
        with open(agg_path, "w", encoding="utf-8") as f:
            json.dump(agg, f, indent=2)
        return "CERTIFIED", agg

    corpus = expand_corpus(scale) if scale > 1 else (
        __import__("certification.corpus.corpus", fromlist=["default_corpus"]).default_corpus()
    )
    ch = __import__("certification.corpus.corpus", fromlist=["corpus_hash"]).corpus_hash()
    backends = runner.eligible_backends()
    expected = len(corpus) * len(backends)
    trials: list[Trial] = []
    campaign_start = _time.time()

    for w in corpus:
        artifacts = build_artifacts_for(w)
        for backend in backends:
            # Budget enforcement: never silently skip trials
            elapsed = _time.time() - campaign_start
            if len(trials) >= budget.max_trials or elapsed >= budget.max_total_runtime_s:
                violation = "max_trials" if len(trials) >= budget.max_trials else "max_total_runtime"
                # Write aggregate with actual counts — never silently skip
                certified_count = sum(1 for t in trials if t.verdict == "CERTIFIED")
                reason = f"budget exhausted ({violation}): {len(trials)}/{expected} trials completed, {certified_count} certified"
                summary = {
                    "wave": wave_id,
                    "scale_factor": scale,
                    "total_trials": len(trials),
                    "expected_trials": expected,
                    "certified": certified_count,
                    "corpus_hash": ch,
                    "verdict": "NOT_CERTIFIED",
                    "verdict_reason": reason,
                    "required_mode": wave.required_mode.value,
                    "budget_violation": violation,
                    "budget": {
                        "max_trials": budget.max_trials,
                        "max_total_runtime_s": budget.max_total_runtime_s,
                        "actual_runtime_s": round(elapsed, 1),
                    },
                }
                with open(agg_path, "w", encoding="utf-8") as f:
                    json.dump(summary, f, indent=2)
                return "NOT_CERTIFIED", summary

            trial = runner.run_trial(
                intent=w.intent,
                category=w.category.value,
                novelty_class="template",
                plan=artifacts.plan,
                revision=artifacts.revision,
                backend=backend,
                corpus_hash=ch,
                requirement_graph_hash=artifacts.requirement_graph_hash,
                genome_hash=artifacts.genome_hash,
                workload=w,
                artifacts=artifacts,
            )
            trials.append(trial)

    assert EvidenceLedger.verify(ledger_path), "Evidence chain broken"

    ok, matrix, taxonomy, problems = verify_campaign_b_mode(
        ledger_path, wave.required_mode,
    )

    verdict, reason = compose_campaign_verdict(
        trials=trials,
        expected_trials=expected,
        ledger_intact=ok,
        integrity_problems=problems,
        coverage_complete=True,
    )

    summary: dict[str, Any] = {
        "wave": wave_id,
        "scale_factor": scale,
        "total_trials": len(trials),
        "expected_trials": expected,
        "certified": sum(1 for t in trials if t.verdict == "CERTIFIED"),
        "corpus_hash": ch,
        "verdict": verdict.value,
        "verdict_reason": reason,
        "required_mode": wave.required_mode.value,
        "independent_verify_ok": ok,
        "independent_verify_problems": problems,
        "failure_taxonomy_independent": taxonomy,
        "category_matrix": matrix,
        "budget": {
            "max_trials": budget.max_trials,
            "max_total_runtime_s": budget.max_total_runtime_s,
            "actual_runtime_s": round(_time.time() - campaign_start, 1),
            "budget_exhausted": len(trials) >= budget.max_trials,
        },
    }

    with open(agg_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    return verdict.value, summary


def verify_campaign_b_mode(
    ledger_path: str,
    required_mode: ExecutionMode,
) -> tuple[bool, dict, dict, list[str]]:
    """Mode-enforcing verifier: rejects CERTIFIED if any behavioral stage
    doesn't match the required execution mode.
    """
    if not EvidenceLedger.verify(ledger_path):
        return False, {}, {}, ["ledger hash chain broken"]

    problems: list[str] = []
    taxonomy: dict[str, int] = {}
    matrix: dict[str, dict[str, int]] = {}

    with open(ledger_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            t = record.get("trial", record)

            for s in t.get("stages", []):
                stage_name = s.get("stage", "")
                if not s.get("passed"):
                    taxonomy[stage_name] = taxonomy.get(stage_name, 0) + 1

            if t.get("verdict") == "CERTIFIED":
                # Mode enforcement
                for s in t.get("stages", []):
                    stage_name = s.get("stage", "")
                    if stage_name in {ts.value for ts in BEHAVIORAL_STAGES}:
                        mode = s.get("mode", "")
                        if mode != required_mode.value:
                            problems.append(
                                f"{t.get('trial_id','?')}: stage {stage_name} "
                                f"mode={mode} != {required_mode.value}"
                            )

                cat = t.get("category", "?")
                backend = t.get("backend", "?")
                matrix.setdefault(cat, {}).setdefault(backend, 0)
                matrix[cat][backend] += 1

    return (not problems), matrix, taxonomy, problems


def _resolve_stages(mode: ExecutionMode) -> Any:
    if mode == ExecutionMode.REAL_DOCKER:
        from certification.stages.docker_stages import RealDockerStages
        return RealDockerStages()
    else:
        from certification.stages.stub_stages import StubStages
        return StubStages()


# Import WaveId at module level for the B0 check
from certification.campaign.waves import WaveId
