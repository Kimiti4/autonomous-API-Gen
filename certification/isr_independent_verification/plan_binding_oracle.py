"""Independent W04 plan-binding oracle (recomputes digests without binding helpers)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from compiler.core.lowering import isr_to_plan
from compiler.core.plan import CompilationPlan
from compiler.core.plan_canonicalization import canonical_bytes_f04
from isr.core.canonicalization_registry import F01_ISR_REVISION, F04_COMPILATION_PLAN
from isr.core.digest_verification import canonical_bytes_f01
from isr.core.revision import ISRRevision

INDEPENDENT_VERIFIER_W04 = "certification.isr_independent_verification.plan_binding_oracle.v1"


@dataclass(frozen=True)
class PlanBindingOracleReport:
    verifier_id: str
    isr_digest_independent_match: bool
    plan_digest_independent_match: bool
    binding_fields_complete: bool
    stale_record_rejected: bool
    tampered_isr_rejected: bool
    findings: tuple[str, ...]


def _independent_isr_digest(revision: ISRRevision) -> str:
    if revision.schema_version not in F01_ISR_REVISION.schema_versions_supported:
        raise ValueError("unsupported-schema")
    return hashlib.sha256(
        canonical_bytes_f01(revision.schema_version, revision.graph)
    ).hexdigest()


def _independent_plan_digest(plan: CompilationPlan) -> str:
    return hashlib.sha256(canonical_bytes_f04(plan)).hexdigest()


def run_plan_binding_oracle(revision: ISRRevision) -> PlanBindingOracleReport:
    findings: list[str] = []
    isr_ok = plan_ok = fields_ok = stale_ok = tamper_ok = False

    try:
        ind_isr = _independent_isr_digest(revision)
        if ind_isr != revision.content_hash:
            findings.append("isr-digest-oracle-mismatch")
        else:
            isr_ok = True
    except Exception as exc:
        findings.append(f"isr:{exc}")

    try:
        plan = isr_to_plan(revision)
        ind_plan = _independent_plan_digest(plan)
        from compiler.core.plan_binding import compute_plan_digest

        if ind_plan != compute_plan_digest(plan):
            findings.append("plan-digest-helpers-vs-oracle-mismatch")
        else:
            plan_ok = True
        from isr.core.canonicalization_registry import get_canonicalization_contract

        c = get_canonicalization_contract(F04_COMPILATION_PLAN.isr_family_id)
        fields_ok = (
            len(ind_isr) == 64
            and len(ind_plan) == 64
            and c.canonicalization_version == F04_COMPILATION_PLAN.canonicalization_version
        )
    except Exception as exc:
        findings.append(f"plan:{exc}")

    try:
        from compiler.core.plan_binding import (
            PlanBindingError,
            build_plan_binding_record,
            verify_plan_binding_record_matches,
        )

        plan = isr_to_plan(revision)
        record = build_plan_binding_record(revision, plan)
        stale = revision.model_copy(update={"revision_id": "stale-rev"})
        try:
            verify_plan_binding_record_matches(stale, plan, record)
            findings.append("stale-record-not-rejected")
        except PlanBindingError:
            stale_ok = True
    except Exception as exc:
        findings.append(f"stale:{exc}")

    try:
        from certification.orchestration.plan_binding_gate import (
            assert_plan_binding_before_compile,
        )

        plan = isr_to_plan(revision)
        bad = revision.model_copy(update={"content_hash": "c" * 64})
        try:
            assert_plan_binding_before_compile(bad, plan)
            findings.append("tampered-isr-not-rejected")
        except Exception:
            tamper_ok = True
    except Exception as exc:
        findings.append(f"tamper:{exc}")

    return PlanBindingOracleReport(
        verifier_id=INDEPENDENT_VERIFIER_W04,
        isr_digest_independent_match=isr_ok,
        plan_digest_independent_match=plan_ok,
        binding_fields_complete=fields_ok,
        stale_record_rejected=stale_ok,
        tampered_isr_rejected=tamper_ok,
        findings=tuple(findings),
    )
