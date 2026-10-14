"""Source-bound orchestration for the universal obligation projection.

This is the shared bridge from a canonical requirement graph into evidence
certification. It verifies source projection and exact suite membership before
runner evidence is considered. It intentionally cannot create consumer bindings
or acceptance scenarios, so an unimplemented application remains UNKNOWN.
"""
from __future__ import annotations

from tiannara.application.compiler.obligation_certification import (
    ObligationCertificationVerdict,
)
from tiannara.application.compiler.obligation_projection import (
    ObligationProjection,
    verify_obligation_projection,
)
from tiannara.application.compiler.trusted_obligation_evidence import (
    TrustedEvidenceStore,
    TrustedObligationSuitePolicy,
    TrustedObligationCertificationRequest,
    certify_trusted_obligation_suite,
)
from collections.abc import Mapping
from tiannara.domain.models.requirement_graph import RequirementGraph


def certify_source_bound_projection(
    graph: RequirementGraph,
    projection: ObligationProjection,
    *,
    policy: TrustedObligationSuitePolicy,
    evidence_store: TrustedEvidenceStore,
    trusted_hmac_keys: Mapping[str, bytes],
    allowed_runner_ids: frozenset[str],
    previously_used_attestation_ids: frozenset[str] = frozenset(),
) -> ObligationCertificationVerdict:
    """Verify graph → projection → policy → evidence without identity substitution.

    The expected source hash is the RequirementGraph hash, never an ISR hash.
    Required suite IDs must exactly equal the MUST obligations in the verified
    projection. Any mismatch is rejected before evidence-store access.
    """
    verify_obligation_projection(graph, projection)
    projected_required = set(projection.required_obligation_ids)
    policy_required = set(policy.required_obligation_ids)
    if policy_required != projected_required:
        raise ValueError(
            "trusted suite required IDs do not exactly match the source projection; "
            f"missing={sorted(projected_required - policy_required)}, "
            f"unexpected={sorted(policy_required - projected_required)}"
        )

    request = TrustedObligationCertificationRequest(
        records=projection.records,
        previously_used_attestation_ids=previously_used_attestation_ids,
    )
    return certify_trusted_obligation_suite(
        request,
        policy=policy,
        expected_source_graph_hash=projection.source_graph_hash,
        evidence_store=evidence_store,
        trusted_hmac_keys=trusted_hmac_keys,
        allowed_runner_ids=allowed_runner_ids,
    )
