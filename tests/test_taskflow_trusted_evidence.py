import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
TRIAL = ROOT / "experiments" / "taskflow-native"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments" / "taskflow-native"))

from provider_free.native_adapter import adapt_taskflow_snapshot  # noqa: E402
from provider_free.trusted_evidence import (  # noqa: E402
    create_envelope_for_signing,
    verify_trusted_resolution_envelope,
)
from tiannara.domain.models.semantic_resolution import (  # noqa: E402
    ResolutionKind,
    SemanticResolution,
    SemanticResolutionRecord,
    TASKFLOW_MANDATORY_FIELDS,
)


def _fixture():
    problem_bytes = (TRIAL / "PROBLEM.md").read_bytes()
    acceptance = json.loads((ROOT / "golden-projects" / "taskflow" / "ACCEPTANCE.json").read_text(encoding="utf-8"))
    import json as json_module
    acceptance_bytes = json_module.dumps(acceptance, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    adapted = adapt_taskflow_snapshot(problem_bytes.decode("utf-8"), acceptance)
    ledger = SemanticResolutionRecord(
        graph_id=adapted.graph.graph_id,
        graph_hash=adapted.graph.content_hash(),
        required_fields=TASKFLOW_MANDATORY_FIELDS,
        resolutions=tuple(
            SemanticResolution(
                field_path=field,
                kind=ResolutionKind.SNAPSHOT,
                value={"reviewed": True, "field": field},
                source="reviewed-canonical-snapshot",
            )
            for field in TASKFLOW_MANDATORY_FIELDS
        ),
    )
    return problem_bytes, acceptance_bytes, adapted.graph, ledger


def test_signed_reviewer_envelope_verifies_exact_snapshot_graph_and_ledger():
    problem_bytes, acceptance_bytes, graph, ledger = _fixture()
    key = b"test-only-trusted-review-key"
    envelope = create_envelope_for_signing(
        record=ledger,
        graph=graph,
        problem_bytes=problem_bytes,
        acceptance_bytes=acceptance_bytes,
        signer_id="test-reviewer",
        trusted_key=key,
    )
    verified, blockers = verify_trusted_resolution_envelope(
        record=ledger,
        graph=graph,
        problem_bytes=problem_bytes,
        acceptance_bytes=acceptance_bytes,
        envelope=envelope,
        trusted_key=key,
    )
    assert verified is True
    assert blockers == ()


def test_envelope_rejects_wrong_key_and_tampered_ledger():
    problem_bytes, acceptance_bytes, graph, ledger = _fixture()
    envelope = create_envelope_for_signing(
        record=ledger,
        graph=graph,
        problem_bytes=problem_bytes,
        acceptance_bytes=acceptance_bytes,
        signer_id="test-reviewer",
        trusted_key=b"correct-test-key",
    )
    verified, blockers = verify_trusted_resolution_envelope(
        record=ledger,
        graph=graph,
        problem_bytes=problem_bytes,
        acceptance_bytes=acceptance_bytes,
        envelope=envelope,
        trusted_key=b"wrong-test-key",
    )
    assert verified is False
    assert any("signature verification failed" in blocker for blocker in blockers)

    changed = ledger.model_copy(update={
        "resolutions": tuple(
            item.model_copy(update={"value": "tampered"}) if item.field_path == TASKFLOW_MANDATORY_FIELDS[0] else item
            for item in ledger.resolutions
        )
    })
    verified, blockers = verify_trusted_resolution_envelope(
        record=changed,
        graph=graph,
        problem_bytes=problem_bytes,
        acceptance_bytes=acceptance_bytes,
        envelope=envelope,
        trusted_key=b"correct-test-key",
    )
    assert verified is False
    assert any("resolution_record_sha256" in blocker or "signature verification failed" in blocker for blocker in blockers)


def test_envelope_requires_out_of_repository_key_and_rejects_missing_envelope():
    problem_bytes, acceptance_bytes, graph, ledger = _fixture()
    verified, blockers = verify_trusted_resolution_envelope(
        record=ledger,
        graph=graph,
        problem_bytes=problem_bytes,
        acceptance_bytes=acceptance_bytes,
        envelope=None,
        trusted_key=None,
    )
    assert verified is False
    assert any("No trusted resolution envelope" in blocker for blocker in blockers)
    assert any("No out-of-repository trusted evidence key" in blocker for blocker in blockers)
