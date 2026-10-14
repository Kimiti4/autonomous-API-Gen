"""Source-bound orchestration for the universal obligation projection."""
from __future__ import annotations

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
from tiannara.domain.models.requirement_graph import RequirementGraph
from tiannara.domain.models.compiler_obligation import ObligationCertificationVerdict if False else Disposition
