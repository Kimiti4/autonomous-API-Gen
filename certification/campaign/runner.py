"""CampaignRunner — orchestrates CBC-1 trials and aggregates results."""
from __future__ import annotations
import json
import os
import tempfile
import uuid
from typing import Any
from compiler.core.plan import CompilationPlan
from compiler.core.conformance import CHECKER
from compiler.core.repository import GeneratedRepository, build_repository
from certification.core.trial import (
    Trial,
    TrialStage,
    StageEvidence,
    compose_verdict,
)
from certification.core import metrics as M
from certification.core.trial import TrialMetrics


def _now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _h(s: str) -> str:
    import hashlib
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


class CampaignRunner:
    """Orchestrates a single CBC-1 trial: compile → stage pipeline → evidence → verdict.

    Stage implementations are injected; for unit tests, use stub stages.
    For behavioral CI, use docker_stages.*
    """

    def __init__(
        self,
        builder: Any = None,
        tester: Any = None,
        deployer: Any = None,
        prober: Any = None,
        destroyer: Any = None,
        verifier: Any = None,
    ) -> None:
        self.builder = builder
        self.tester = tester
        self.deployer = deployer
        self.prober = prober
        self.destroyer = destroyer
        self.verifier = verifier

    def run_trial(
        self,
        intent: str,
        category: str,
        novelty_class: str,
        plan: CompilationPlan,
        revision_id: str,
        backend: Any,
        backend_test_cmd: list[str] | None = None,
    ) -> Trial:
        trial_id = str(uuid.uuid4())

        repo = backend.compile(plan)

        d = tempfile.mkdtemp(prefix="cbc1-")
        for p, c in repo.files.items():
            full = os.path.join(d, p)
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w", encoding="utf-8") as f:
                f.write(c)

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

        # Structural + semantic via backend conformance
        conf = backend.conformance(plan, repo)
        _record(TrialStage.STRUCTURAL, conf.passed, f"missing={conf.missing}")
        _record(TrialStage.SEMANTIC, conf.passed, f"semantic={conf.passed}")

        # Build
        if self.builder:
            tag = f"cbc1-{trial_id[:8]}"
            b_ok, b_hash = self.builder.build(d, tag)
            _record(TrialStage.BUILD, b_ok, f"build_hash={b_hash}")
        else:
            _record(TrialStage.BUILD, True, "stub-build")

        # Test
        if self.tester and backend_test_cmd:
            image = f"cbc1-{trial_id[:8]}"
            t_ok, t_hash = self.tester.run_tests(image, backend_test_cmd)
            _record(TrialStage.TEST, t_ok, f"test_hash={t_hash}")
        else:
            _record(TrialStage.TEST, True, "stub-test")

        # Deploy
        cid = ""
        if self.deployer:
            d_ok, cid = self.deployer.deploy(f"cbc1-{trial_id[:8]}", 8000 + hash(trial_id) % 1000)
            _record(TrialStage.DEPLOY, d_ok, f"cid={cid}")
        else:
            _record(TrialStage.DEPLOY, True, "stub-deploy")

        # Runtime
        if self.prober:
            port = 8000 + hash(trial_id) % 1000
            r_ok = self.prober.probe(port)
            _record(TrialStage.RUNTIME, r_ok, f"runtime_ok={r_ok}")
        else:
            _record(TrialStage.RUNTIME, True, "stub-runtime")

        # Destroy
        if self.destroyer and cid:
            x_ok = self.destroyer.destroy(cid)
            _record(TrialStage.DESTROY, x_ok, f"destroy_ok={x_ok}")
        else:
            _record(TrialStage.DESTROY, True, "stub-destroy")

        # Independent verify (separate process)
        if self.verifier:
            import hashlib
            plan_hash = hashlib.sha256(
                json.dumps(sorted(backend.element_paths(plan).values())).encode("utf-8")
            ).hexdigest()
            plan_path = os.path.join(d, ".plan.json")
            with open(plan_path, "w") as f:
                json.dump({"expected_paths": list(backend.element_paths(plan).values())}, f)
            v_ok = self.verifier.verify(d, plan_hash, plan_path)
            _record(TrialStage.VERIFY, v_ok, f"verify_ok={v_ok}")
        else:
            _record(TrialStage.VERIFY, True, "stub-verify")

        # Metrics
        metrics = M.compute(
            repo_files_count=len(repo.files),
            stages=stage_results,
            structural_passed=stage_results.get(TrialStage.STRUCTURAL, False),
            test_passed=stage_results.get(TrialStage.TEST, False),
            runtime_passed=stage_results.get(TrialStage.RUNTIME, False),
            repo_content_hash=repo.content_hash,
        )

        verdict = compose_verdict(stage_results, evidence_present=True)

        return Trial(
            trial_id=trial_id,
            intent=intent,
            category=category,
            novelty_class=novelty_class,
            requirement_graph_hash="",
            genome_hash="",
            isr_revision_id=revision_id,
            backend=backend.name,
            compiler_version="1.4.0",
            repo_hash=repo.content_hash,
            stages=evidence,
            metrics=metrics,
            verdict=verdict,
        )


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
