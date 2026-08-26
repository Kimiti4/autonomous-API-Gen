"""ProvenanceBundle — self-describing .tiannara/ per-trial provenance.

The bundle is excluded from the application content hash.  It carries the
full chain: corpus_hash → requirement_graph_hash → genome_hash →
isr_content_hash → plan_hash → backend identity/version → app repo_hash.

The bundle is a record, not the authority.  Certification authority remains
the independent verifier + the hash-chained evidence ledger.
"""
from __future__ import annotations
import hashlib
import json
import os
from typing import Any, Mapping


def _canon(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


class ProvenanceBundle:
    """Emits the self-describing .tiannara/ bundle for one trial."""

    @staticmethod
    def emit(
        *,
        trial: Any,
        plan: Any,
        revision: Any,
        genome: Any,
        requirement_graph: Any,
        backend_identity: Any,
        conformance: Any,
        ledger_record_hash: str = "",
    ) -> dict[str, str]:
        isr_json = _canon(revision.model_dump())
        genome_json = _canon(genome.model_dump())
        rg_json = _canon(requirement_graph.model_dump())

        provenance = {
            "intent": trial.intent,
            "category": trial.category,
            "novelty_class": trial.novelty_class,
            "corpus_hash": getattr(trial, "corpus_hash", ""),
            "requirement_graph_hash": _sha(rg_json),
            "genome_hash": _sha(genome_json),
            "isr_revision_id": revision.revision_id,
            "isr_content_hash": revision.content_hash,
            "plan_hash": _sha(_canon(plan.model_dump())),
            "backend": backend_identity.name,
            "backend_version": backend_identity.version,
            "backend_class": backend_identity.backend_class.value,
            "application_repo_hash": trial.repo_hash,
        }

        trial_json = {k: v for k, v in trial.model_dump().items()}

        return {
            ".tiannara/trial.json": _canon(trial_json),
            ".tiannara/provenance.json": _canon(provenance),
            ".tiannara/requirement-graph.json": rg_json,
            ".tiannara/genome.json": genome_json,
            ".tiannara/isr.json": isr_json,
            ".tiannara/isr-hash": revision.content_hash + "\n",
            ".tiannara/compiler.json": _canon({
                "backend": backend_identity.name,
                "language": backend_identity.language,
                "framework": backend_identity.framework,
                "version": backend_identity.version,
                "backend_class": backend_identity.backend_class.value,
                "element_paths": {},
                "conformance": conformance.model_dump(),
            }),
            ".tiannara/certification.json": _canon({
                "trial_id": trial.trial_id,
                "verdict": trial.verdict,
                "stages": [s.model_dump() for s in trial.stages],
                "ledger_record_hash": ledger_record_hash,
            }),
            ".tiannara/evidence-manifest.json": _canon({
                "record_hash": ledger_record_hash,
                "stage_logs": [
                    {"stage": s.stage.value, "logs_hash": s.logs_hash}
                    for s in trial.stages
                ],
            }),
        }

    @staticmethod
    def bundle_hash(files: Mapping[str, str]) -> str:
        return _sha(_canon({k: files[k] for k in sorted(files)}))

    @staticmethod
    def verify_bundle(repo_dir: str) -> dict[str, bool]:
        """Independent check: recompute application hash excluding .tiannara/,
        and validate the bundle's internal hash chain."""
        app: dict[str, str] = {}
        bundle: dict[str, str] = {}
        for root, _, fs in os.walk(repo_dir):
            for f in fs:
                full = os.path.join(root, f)
                rel = os.path.relpath(full, repo_dir).replace(os.sep, "/")
                try:
                    content = open(full, encoding="utf-8", errors="replace").read()
                except Exception:
                    content = ""
                if rel.startswith(".tiannara/"):
                    bundle[rel] = content
                else:
                    app[rel] = content

        from compiler.core.repository import build_repository
        app_hash = build_repository(app).content_hash

        prov = json.loads(bundle.get(".tiannara/provenance.json", "{}"))
        isr = json.loads(bundle.get(".tiannara/isr.json", "{}"))
        genome = json.loads(bundle.get(".tiannara/genome.json", "{}"))
        rg_content = bundle.get(".tiannara/requirement-graph.json", "")

        genome_raw = bundle.get(".tiannara/genome.json", "")
        checks: dict[str, bool] = {
            "application_hash": app_hash == prov.get("application_repo_hash", ""),
            "isr_content": (
                isr.get("content_hash") == prov.get("isr_content_hash", "")
                and bundle.get(".tiannara/isr-hash", "").strip() == prov.get("isr_content_hash", "")
            ),
            "genome_hash": _sha(genome_raw) == prov.get("genome_hash", "") if genome_raw else False,
            "rg_hash": _sha(rg_content) == prov.get("requirement_graph_hash", ""),
        }
        checks["all"] = all(checks.values())
        return checks
