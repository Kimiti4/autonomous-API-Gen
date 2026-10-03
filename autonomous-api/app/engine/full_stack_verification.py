"""End-to-end full-stack engineering verification gate."""
from __future__ import annotations
from dataclasses import dataclass
from .api_ir import ApiContractIR
from .implementation_ir import BackendIR, FrontendIR
from .cross_layer_coherence import CoherenceFinding, verify_cross_layer_coherence
from .effect_coherence import EffectPath, EffectCoherenceFinding, verify_effect_coherence
from .effect_consequences import EffectConsequence, ConsequenceFinding, verify_effect_consequences


@dataclass(frozen=True)
class FullStackVerification:
    coherence: tuple[CoherenceFinding, ...]
    effects: tuple[EffectCoherenceFinding, ...]
    consequences: tuple[ConsequenceFinding, ...]

    @property
    def passed(self) -> bool:
        return not (self.coherence or self.effects or self.consequences)

    @property
    def findings(self) -> tuple[object, ...]:
        return self.coherence + self.effects + self.consequences


def verify_full_stack(
    frontend: FrontendIR,
    api: ApiContractIR,
    backend: BackendIR,
    effects: tuple[EffectPath, ...] = (),
    consequences: tuple[EffectConsequence, ...] = (),
) -> FullStackVerification:
    coherence = verify_cross_layer_coherence(frontend, api, backend)
    effect_findings = verify_effect_coherence(frontend, api, backend, effects)
    consequence_findings = verify_effect_consequences(effects, consequences, backend)
    return FullStackVerification(coherence, effect_findings, consequence_findings)
