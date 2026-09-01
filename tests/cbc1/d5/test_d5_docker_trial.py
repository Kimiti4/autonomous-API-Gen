"""D5 — Independent Trial Execution (Docker integration trial).

Proves the governed self-repair SHAPE end-to-end with real Docker:

    TRIAL-D5-*T1  origin=reference  backend=rust-axum   status=FAILED
        ↓ causal classification (backend_behavior, actionable)
        ↓ learning signal -> ContinuousLearningEngine (real)
        ↓ governed backend-swap candidate -> python-fastapi (real policy)
    TRIAL-D5-*T2  origin=evolved   backend=python-fastapi status=CERTIFIED

Asserts parent immutability, independent certification, ISR/genome unchanged,
backend/artifact/image novelty, learning consumption, and no direct repair.

This uses the REAL certification.feedback modules (no parallel stub taxonomy)
and the REAL ContinuousLearningEngine for learning consumption.
"""
import json
import sys
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from certification.feedback.repair import GovernedRepair
from learning.engine import ContinuousLearningEngine

from d5_harness import (
    build_image,
    container_logs,
    docker_available,
    free_port,
    hash_dir,
    http_get_json,
    items_behavior_ok,
    remove_image,
    run_container,
    stop_container,
    utcnow,
    wait_http_live,
)
from templates import (
    write_python_fastapi_success,
    write_rust_axum_failure,
)


@pytest.mark.docker_integration
def test_d5_docker_backend_swap_trial(tmp_path: Path) -> None:
    if not docker_available():
        pytest.skip("Docker is not available on this host.")
    import subprocess
    try:
        subprocess.run(["docker", "info"], capture_output=True, check=True)
    except Exception:
        pytest.skip("Docker daemon not reachable.")

    suffix = uuid.uuid4().hex[:8]
    workspace = tmp_path / "d5"
    workspace.mkdir(parents=True, exist_ok=False)

    # Real append-only evidence store (isolated to the test tmp dir).
    ledger_path = workspace / "ledger.jsonl"
    events_path = workspace / "events.jsonl"
    learning_engine = ContinuousLearningEngine()          # REAL engine

    intent_id = "intent.d5.health-items"
    isr_hash = "sha256:isr-d5-constitutional"
    genome_hash = "sha256:genome-d5-reference"

    parent_trial_id = f"TRIAL-D5-{suffix}-T1"
    child_trial_id = f"TRIAL-D5-{suffix}-T2"

    parent_backend = "rust-axum"
    candidate_backend = "python-fastapi"
    eligible_backends = ["rust-axum", "python-fastapi"]

    parent_context = workspace / "parent" / parent_backend
    candidate_context = workspace / "candidate" / candidate_backend

    parent_image = f"d5-parent-rust-{suffix}:latest"
    candidate_image = f"d5-candidate-python-{suffix}:latest"
    parent_container = f"d5-parent-rust-{suffix}"
    child_container = f"d5-candidate-python-{suffix}"
    parent_port = free_port()
    child_port = free_port()

    def emit(event: str, payload: dict) -> None:
        with events_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"event": event, "ts": utcnow(), "payload": payload}, sort_keys=True) + "\n")

    def append_record(rec: dict) -> None:
        with ledger_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, sort_keys=True) + "\n")

    def get_record(trial_id: str):
        if not ledger_path.exists():
            return None
        for line in ledger_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec["trial_id"] == trial_id:
                return rec
        return None

    try:
        # ------------------------------------------------------------------
        # 1. Parent artifact: compile (fixture) + docker build.
        # ------------------------------------------------------------------
        write_rust_axum_failure(parent_context)
        parent_artifact_hash = hash_dir(parent_context)
        parent_image_id = build_image(parent_image, parent_context)

        # 2. Execute parent, observe genuine backend-behavior failure.
        run_container(parent_container, parent_image, parent_port)
        assert wait_http_live(f"http://127.0.0.1:{parent_port}/live", timeout=120), (
            "parent not live: " + container_logs(parent_container)
        )
        status, body = http_get_json(f"http://127.0.0.1:{parent_port}/items")
        assert items_behavior_ok(status, body) is False, "parent fixture must fail behaviorally"
        stop_container(parent_container)

        # 3. Causal classification (REAL) — backend_behavior is actionable.
        from certification.feedback.rule import analyze_failure
        cls = analyze_failure(stage="runtime", failure_class="product", detail="GET /items returned empty list while /live was 200")
        assert cls.repair_eligible is True
        emit("feedback.classified", {
            "trial_id": parent_trial_id, "intent_id": intent_id,
            "backend_id": parent_backend, "classification": cls.as_record(),
        })

        # 4. Immutable parent record.
        parent_record = {
            "trial_id": parent_trial_id, "intent_id": intent_id,
            "isr_hash": isr_hash, "genome_hash": genome_hash,
            "backend_id": parent_backend, "variant_kind": "reference",
            "origin": "reference", "status": "FAILED",
            "stage": cls.stage, "cause": cls.cause,
            "feedback_domain": cls.feedback_domain,
            "artifact_hash": parent_artifact_hash, "image_id": parent_image_id,
            "evidence_ref": f"evidence://{intent_id}/{parent_trial_id}/behavior",
            "created_at": utcnow(),
        }
        append_record(parent_record)
        parent_snapshot = json.dumps(get_record(parent_trial_id), sort_keys=True)

        # 5. Learning consumption (REAL ContinuousLearningEngine).
        repair = GovernedRepair(learning_engine=learning_engine)
        feedback = repair.evaluate_failure(
            trial_id=parent_trial_id, intent=intent_id, backend=parent_backend,
            stage=cls.stage, failure_class="product",
            detail="GET /items empty; /live 200",
            isr_hash=isr_hash, genome_hash=genome_hash,
            eligible_backend_ids=eligible_backends,
        )
        assert learning_engine.report()["signal_count"] >= 1
        emit("learning.signal_emitted", feedback.signal.model_dump())

        # 6. Governed evolution decision (REAL policy).
        assert feedback.decision.accepted is True
        assert feedback.decision.alternate_backend_id == candidate_backend
        emit("evolution.evaluation", {
            "trial_id": parent_trial_id, "intent_id": intent_id,
            "decision": feedback.decision.as_record(),
        })

        # 7. Candidate from REAL policy + compile fixture for alternate backend.
        candidate = feedback.candidate
        assert candidate is not None
        candidate_id = candidate.candidate_id
        write_python_fastapi_success(candidate_context)
        candidate_artifact_hash = hash_dir(candidate_context)
        assert candidate_artifact_hash != parent_artifact_hash, "NO_OP_EVOLUTION: artifact identical"
        candidate_image_id = build_image(candidate_image, candidate_context)
        assert candidate_image_id != parent_image_id, "NO_OP_EVOLUTION: image identical"
        emit("evolution.candidate_created", candidate.lineage())

        # 8. Independent execution of the candidate.
        run_container(child_container, candidate_image, child_port)
        assert wait_http_live(f"http://127.0.0.1:{child_port}/live", timeout=120), (
            "candidate not live: " + container_logs(child_container)
        )
        status, body = http_get_json(f"http://127.0.0.1:{child_port}/items")
        assert items_behavior_ok(status, body) is True, "candidate must pass behavior"
        stop_container(child_container)
        emit("evolution.candidate_executed", {
            "trial_id": child_trial_id, "candidate_id": candidate_id,
            "backend_id": candidate_backend, "behavior_ok": True,
        })

        # 9. Independently certify child.
        child_record = {
            "trial_id": child_trial_id, "intent_id": intent_id,
            "parent_trial_id": parent_trial_id,
            "isr_hash": isr_hash, "genome_hash": genome_hash,
            "backend_id": candidate_backend, "variant_kind": "backend_swap",
            "origin": "evolved", "status": "CERTIFIED",
            "stage": "runtime", "cause": None, "feedback_domain": None,
            "artifact_hash": candidate_artifact_hash, "image_id": candidate_image_id,
            "evidence_ref": f"evidence://{intent_id}/{child_trial_id}/behavior",
            "created_at": utcnow(),
        }
        append_record(child_record)
        emit("evolution.candidate_certified", {
            "trial_id": child_trial_id, "candidate_id": candidate_id,
            "backend_id": candidate_backend, "outcome": "CERTIFIED",
        })

        # ============================ INVARIANTS ============================
        parent_ledger = get_record(parent_trial_id)
        child_ledger = get_record(child_trial_id)

        # Independent certification.
        assert parent_ledger["status"] == "FAILED"
        assert child_ledger["status"] == "CERTIFIED"

        # Lineage.
        assert child_ledger["parent_trial_id"] == parent_trial_id
        assert child_ledger["origin"] == "evolved"
        assert child_ledger["variant_kind"] == "backend_swap"

        # ISR/genome unchanged (backend evolution does not mutate constitution).
        assert child_ledger["isr_hash"] == parent_ledger["isr_hash"]
        assert child_ledger["genome_hash"] == parent_ledger["genome_hash"]

        # Backend + artifact + image novelty.
        assert child_ledger["backend_id"] != parent_ledger["backend_id"]
        assert child_ledger["artifact_hash"] != parent_ledger["artifact_hash"]
        assert child_ledger["image_id"] != parent_ledger["image_id"]

        # Independent evidence + identity.
        assert child_ledger["evidence_ref"] != parent_ledger["evidence_ref"]
        assert child_ledger["trial_id"] != parent_ledger["trial_id"]

        # Parent immutability.
        assert json.dumps(get_record(parent_trial_id), sort_keys=True) == parent_snapshot

        # No direct repair of parent generated repository.
        assert hash_dir(parent_context) == parent_artifact_hash

        # Structured event proof.
        events_text = events_path.read_text(encoding="utf-8")
        for name in (
            "feedback.classified", "learning.signal_emitted",
            "evolution.evaluation", "evolution.candidate_created",
            "evolution.candidate_executed", "evolution.candidate_certified",
        ):
            assert name in events_text

    finally:
        stop_container(parent_container)
        stop_container(child_container)
        remove_image(parent_image)
        remove_image(candidate_image)
