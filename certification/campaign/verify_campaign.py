"""Independent campaign verifier — re-reads ledger, rejects forged/incomplete CERTIFIED."""
from __future__ import annotations
import json
from collections import defaultdict

from certification.core.trial import TrialStage
from certification.evidence.ledger import EvidenceLedger
from compiler.core.protocol import BEHAVIORAL_CLASSES

REQUIRED_STAGES = {s.value for s in (
    TrialStage.STRUCTURAL, TrialStage.SEMANTIC, TrialStage.BUILD,
    TrialStage.TEST, TrialStage.DEPLOY, TrialStage.RUNTIME,
    TrialStage.DESTROY, TrialStage.VERIFY,
)}


def verify_campaign(ledger_path: str) -> tuple[bool, dict, dict, list[str]]:
    """Verify the full campaign ledger.

    Returns (ok, matrix, taxonomy, problems).
    ok is False if ANY dishonest or incomplete CERTIFIED trial is found.
    """
    if not EvidenceLedger.verify(ledger_path):
        return False, {}, {}, ["ledger hash chain broken"]

    problems: list[str] = []
    matrix: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    taxonomy: dict[str, int] = defaultdict(int)

    with open(ledger_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            t = record.get("trial", record)

            stages_seen: set[str] = set()
            for s in t.get("stages", []):
                stages_seen.add(s["stage"])
                if not s["passed"]:
                    taxonomy[s["stage"]] += 1

            if t.get("verdict") == "CERTIFIED":
                bc = t.get("backend_class", "")
                if bc not in {c.value for c in BEHAVIORAL_CLASSES}:
                    problems.append(
                        f"{t.get('trial_id','?')}: CERTIFIED with backend_class={bc}"
                    )
                missing = REQUIRED_STAGES - stages_seen
                if missing:
                    problems.append(
                        f"{t.get('trial_id','?')}: missing stages {sorted(missing)}"
                    )
                matrix[t.get("category", "?")][t.get("backend", "?")] += 1

    return (not problems), dict(matrix), dict(taxonomy), problems
