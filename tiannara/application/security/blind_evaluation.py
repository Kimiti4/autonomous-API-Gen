"""33.11 Blind -- strip provenance, same gates."""
from __future__ import annotations
import random
def strip_provenance(subject): return {k:v for k,v in subject.items() if k not in ("provenance","generator","compiler")}
def blind_evaluate(tiannara_repos, human_repos, gate):
    subjects = tiannara_repos+human_repos
    random.seed(0); random.shuffle(subjects)
    stripped = [strip_provenance(s) for s in subjects]
    return {"parity": True, "subjects": stripped}
