import hashlib
import json
from pathlib import Path
from ...domain.models.evidence import CertificationEvidence


def _fingerprint(previous_hash: str | None, evidence: CertificationEvidence) -> str:
    payload = evidence.model_dump_json(exclude={"record_hash"})
    return hashlib.sha256(f"{previous_hash or ''}:{payload}".encode("utf-8")).hexdigest()


class JsonlEvidenceLedger:
    """Append-only JSONL evidence ledger with a SHA-256 record-hash chain.

    Satisfies :class:`EvidenceLedger`. Tamper evidence: altering any stored
    record (content or hash) invalidates ``verify_chain`` from that record on.
    """

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, evidence: CertificationEvidence) -> CertificationEvidence:
        previous_hash = self._last_hash()
        evidence.previous_hash = previous_hash
        evidence.record_hash = _fingerprint(previous_hash, evidence)
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(evidence.model_dump_json() + "\n")
        return evidence

    def verify_chain(self) -> bool:
        if not self._path.exists():
            return True
        previous_hash: str | None = None
        for line in self._path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            raw = json.loads(line)
            stored = raw.get("record_hash")
            if raw.get("previous_hash") != previous_hash:
                return False
            rebuilt = CertificationEvidence.model_validate(
                {k: v for k, v in raw.items() if k != "record_hash"}
            )
            if _fingerprint(previous_hash, rebuilt) != stored:
                return False
            previous_hash = stored
        return True

    def all(self) -> list[CertificationEvidence]:
        if not self._path.exists():
            return []
        return [
            CertificationEvidence.model_validate(json.loads(line))
            for line in self._path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def query(
        self,
        *,
        project_id: str | None = None,
        isr_hash: str | None = None,
        backend_name: str | None = None,
        verdict=None,
    ) -> list[CertificationEvidence]:
        """Read-side indexing for Phase 20/38 consumption (additive; no chain effect).

        Filters are conjunctive; ``None`` means "any." Returns records in append
        order. Tooling that only needs append/verify/chain-integrity is unaffected.
        """
        records = self.all()
        if project_id is not None:
            records = [r for r in records if r.project_id == project_id]
        if isr_hash is not None:
            records = [r for r in records if r.isr_hash == isr_hash]
        if backend_name is not None:
            records = [r for r in records if r.backend_name == backend_name]
        if verdict is not None:
            records = [r for r in records if r.verdict == verdict]
        return records

    def _last_hash(self) -> str | None:
        if not self._path.exists():
            return None
        lines = [ln for ln in self._path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        if not lines:
            return None
        return json.loads(lines[-1]).get("record_hash")
