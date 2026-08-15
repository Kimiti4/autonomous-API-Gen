import json

from tiannara.infrastructure.ledger.jsonl_evidence_ledger import JsonlEvidenceLedger
from tiannara.interfaces.cli.main import main


def _env(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TIANNARA_FALLBACK_OWNER", "t")
    monkeypatch.setenv("TIANNARA_FALLBACK_EMAIL", "t@t.t")
    monkeypatch.setenv("TIANNARA_LEDGER_PATH", str(tmp_path / "evidence.jsonl"))
    monkeypatch.setenv("TIANNARA_QUARANTINE_DIR", str(tmp_path / "quarantine"))
    monkeypatch.setenv("TIANNARA_ENVIRONMENT", "local")


def test_cli_run_calibration_and_verify_ledger(tmp_path, monkeypatch):
    _env(monkeypatch, tmp_path)
    (tmp_path / "manifest.json").write_text(json.dumps({"projects": [
        {"id": "cli-1", "intent": "a hello service", "domain": "general",
         "target_backend": "minimal-container", "complexity_tier": "simple"}]}),
        encoding="utf-8")
    assert main(["run-calibration", "--manifest", str(tmp_path / "manifest.json")]) == 0
    assert (tmp_path / "tiannara-published" / "cli-1").exists()
    assert main(["verify-ledger", "--ledger", str(tmp_path / "evidence.jsonl")]) == 0


def test_cli_verify_ledger_detects_tamper(tmp_path, monkeypatch):
    _env(monkeypatch, tmp_path)
    (tmp_path / "m.json").write_text(json.dumps({"projects": [
        {"id": "t1", "intent": "hi", "domain": "d", "target_backend": "minimal-container"}]}),
        encoding="utf-8")
    assert main(["run-calibration", "--manifest", str(tmp_path / "m.json")]) == 0

    path = tmp_path / "evidence.jsonl"
    lines = path.read_text(encoding="utf-8").splitlines()
    rec = json.loads(lines[0])
    rec["isr_hash"] = "tampered"
    lines[0] = json.dumps(rec)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert main(["verify-ledger", "--ledger", str(path)]) == 1
