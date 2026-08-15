"""
Phase 28 — Governance console renderer (Milestone 5A).

Builds a self-contained, read-mostly HTML console (console.html) from live
kernel state, following the HIL prototype convention: one static artifact
with state embedded as JSON. The console presents the eight dashboard views
(health, constitution/policy, evaluations, decision dossier, approvals,
exceptions, audit log, lineage) with no backend of its own — the kernel is
the only system of record.

Usage:
    python -m constitutional_architecture.governance.dashboard.render_console \
        [--out PATH] [--json SNAPSHOT.json] [--demo]

  --out PATH    output html path (default: governance/dashboard/console.html)
  --json FILE   rebuild the console from a previously rendered snapshot
  --demo        build a demo kernel with example evaluations/approvals and
                render it (used for validation and documentation)
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from constitutional_architecture.governance.dashboard.service import DashboardService
from constitutional_architecture.governance.audit import decision_id_of
from constitutional_architecture.governance.kernel import GovernanceKernel
from constitutional_architecture.governance.schemas import (
    Actor,
    ActorType,
    ApprovalDecision,
    GovernanceEvaluationRequest,
)

TEMPLATE_PATH = Path(__file__).with_name("console.html")


def build_demo_kernel() -> GovernanceKernel:
    """A deterministic demo kernel with one approved promotion and one
    rejected one, an exception, and lineage links."""
    kernel = GovernanceKernel()
    from constitutional_architecture.governance import ALL_POLICY_PACKS

    constitution = kernel.create_constitution(
        name="Platform Constitution",
        description="Root constitutional governance.",
        policy_domains=[
            "isr_integrity",
            "autonomy_bounds",
            "safety_verification",
            "reversibility",
            "auditability",
        ],
    )
    kernel.activate_constitution(constitution.id)
    for pack_name, rules in ALL_POLICY_PACKS.items():
        policy_set = kernel.create_policy_set(
            name=pack_name,
            constitution_id=constitution.id,
            constitution_version=constitution.version,
            rule_definitions=rules,
        )
        kernel.activate_policy_set(policy_set.id)

    agent = Actor(
        actor_type=ActorType.AUTONOMOUS_AGENT,
        actor_id="evolution_agent_01",
        roles=["evolution_proposer"],
        delegated_authority=["propose_isr_changes"],
    )
    human = Actor(
        actor_type=ActorType.HUMAN,
        actor_id="alice",
        roles=["auditor", "platform_operator"],
    )

    def promote(subject_id: str, **context_overrides) -> tuple:
        request = GovernanceEvaluationRequest(
            subject_type="EVOLUTION_PROPOSAL",
            subject_id=subject_id,
            action="PROMOTE",
            actor=agent,
            context={
                "environment": "staging",
                "has_rollback_plan": True,
                "verification_status": "passed",
                "parent_hash": f"h_{subject_id}",
                "content_hash": f"h_{subject_id}_content",
                "audit_commitment": True,
                **context_overrides,
            },
            evidence_refs=["verification_report", "simulation_report"],
        )
        evaluation = kernel.evaluate(request)
        approval_ids = kernel.create_approvals(evaluation)
        for approval_id in approval_ids:
            kernel.submit_approval(approval_id, ApprovalDecision.APPROVED)
        final = kernel.finalize(
            evaluation,
            subject_type=request.subject_type,
            subject_id=request.subject_id,
            action=request.action,
            actor=request.actor,
        )
        return request, evaluation, final

    _, evaluation_a, _ = promote("prop_engine_refactor")
    kernel.record_lineage(
        parent_artifact_type="ISR_REVISION",
        parent_artifact_id="isr_rev_100",
        parent_artifact_hash="h_100",
        child_artifact_type="ISR_REVISION",
        child_artifact_id="isr_rev_101",
        child_artifact_hash="h_101",
        change_type="PROMOTION",
        decision_ref=decision_id_of(evaluation_a),
    )

    promote("prop_backend_migration", has_rollback_plan=False)

    kernel.create_exception(
        "temp_dev_widget",
        "Temporary widget development until the widget module ships.",
        granted_by="alice",
    )
    return kernel


def collect_snapshot(kernel: GovernanceKernel) -> dict:
    dashboard = DashboardService(kernel)
    evaluations = dashboard.evaluations()
    decision_ids = {e["decision_id"] for e in evaluations}
    for item in evaluations:
        item["lineage"] = [
            l.model_dump()
            for l in kernel.lineage.all()
            if l.decision_ref == item["decision_id"]
        ]
        item["audit"] = [
            e.model_dump()
            for e in kernel.audit_events(decision_id=item["decision_id"])
        ]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "health": dashboard.health(),
        "constitutions": dashboard.constitution_overview()["constitutions"],
        "active_constitutions": dashboard.constitution_overview()["active_constitutions"],
        "policy_sets": dashboard.constitution_overview()["policy_sets"],
        "evaluations": evaluations,
        "approvals": dashboard.approvals(),
        "exceptions": dashboard.exceptions(),
        "audit_events": dashboard.audit_events(),
        "chain": dashboard.verify_chain(),
        "lineage": [l.model_dump() for l in kernel.lineage.all()],
    }


def render(snapshot: dict, out_path: Path) -> Path:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    embedded = json.dumps(snapshot, indent=2, default=str)
    html = template.replace("__GOVDATA__", embedded)
    out_path.write_text(html, encoding="utf-8")
    return out_path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", type=Path, default=TEMPLATE_PATH)
    parser.add_argument("--json", type=Path, default=None, help="snapshot json to embed")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="build and render a demo kernel state",
    )
    args = parser.parse_args(argv)

    if args.json is not None:
        snapshot = json.loads(args.json.read_text(encoding="utf-8"))
    elif args.demo:
        snapshot = collect_snapshot(build_demo_kernel())
    else:
        parser.error("provide --json SNAPSHOT.json or --demo")
        return 1

    out = render(snapshot, args.out)
    print(f"Rendered governance console: {out} ({out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
