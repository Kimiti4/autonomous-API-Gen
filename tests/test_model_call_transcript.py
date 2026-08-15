import json

from tiannara.domain.models.model_call import ModelCallRecord
from tiannara.infrastructure.llm.transcript import ModelCallTranscript


def _record(sig: str, payload=None) -> ModelCallRecord:
    return ModelCallRecord(
        signature_hash=sig, model_id="stub@1", task="t",
        output_schema_id="s.v1", output_payload=payload,
        response_hash="x" if payload is not None else "",
    )


def test_append_builds_valid_chain(tmp_path):
    transcript = ModelCallTranscript(tmp_path / "t.jsonl")
    transcript.append(_record("sig-a", {"v": 1}))
    transcript.append(_record("sig-b", {"v": 2}))
    assert transcript.verify_chain() is True


def test_tamper_breaks_chain(tmp_path):
    path = tmp_path / "t.jsonl"
    transcript = ModelCallTranscript(path)
    transcript.append(_record("sig-a", {"v": 1}))
    transcript.append(_record("sig-b", {"v": 2}))
    lines = path.read_text().splitlines()
    rec = json.loads(lines[0])
    rec["output_payload"]["v"] = 999
    lines[0] = json.dumps(rec, separators=(",", ":"))
    path.write_text("\n".join(lines) + "\n")
    assert transcript.verify_chain() is False


def test_index_skips_failed_and_empty(tmp_path):
    transcript = ModelCallTranscript(tmp_path / "t.jsonl")
    transcript.append(_record("ok", {"v": 1}))
    transcript.append(_record("empty", None))
    index = transcript.index_by_signature()
    assert set(index.keys()) == {"ok"}
