"""R2 -- Evolution Engine application package.

Technology-neutral evolution primitives: failure classification (R2.1/R2.2),
the candidate sandbox, mutation operators, and the causal ledger (R2.6).
"""
from tiannara.application.evolution.candidate_sandbox import (
    CandidateSandbox,
    CompiledCandidate,
    RunResult,
    attempt_repair_cycle,
)
from tiannara.application.evolution.candidate_gate import (
    BrokenTreeIntactInvariant,
    CandidateGate,
    CandidateVerdict,
    Gate,
    GateContext,
    GateResult,
    PerformanceGate,
    ProtectedInvariant,
    SecurityGate,
)
from tiannara.application.evolution.ledger import (
    EvolutionLedger,
    EvolutionEvent,
    EvolutionRecord,
    EventType,
    SelectionRecord,
    project_record,
    project_selection,
    stable_isr_hash,
)
from tiannara.application.evolution.transition_restoration import (
    RepairedCandidate,
    TransitionRestoration,
    apply_restoration,
)
from tiannara.application.evolution.compiler_sandbox import (
    RealBackendSandbox,
    docker_available,
    hash_artifact,
    hash_run,
)
from tiannara.application.evolution.fitness import (
    FitnessVector,
    ScoredCandidate,
    compute_fitness,
)
from tiannara.application.evolution.mutation_operators import (
    EMPTY_DELTA,
    ISRDelta,
    MutationCandidate,
    MutationOperator,
    NullMutation,
    TransitionRestorationOperator,
)
from tiannara.application.evolution.competitive_evolution import (
    CompetitiveEvolutionCoordinator,
    DeterministicComplexityPreference,
    EliteAdvancementStrategy,
    SelectionDecision,
    SelectionStrategy,
    pareto_frontier,
    score_candidate,
)
from tiannara.application.evolution.variation import (
    ActionInjectionOperator,
    AwaitingSurfaceIntactInvariant,
    ConstructiveVariationOperator,
    CrossoverOperator,
    FSMRepairVariation,
    GuardRelaxationOperator,
    NullCrossover,
    RandomFSMExploration,
    TestDeletionMutation,
)
from tiannara.application.evolution.autonomous_repair import (
    AutonomousRepairCoordinator,
    AutonomousRepairResult,
)
from tiannara.application.evolution.evolution_state import (
    DiversityMetrics,
    EvolutionState,
    GenerationState,
    PopulationSnapshot,
    TerminationReason,
    derive_evolution_id,
    derive_generation_id,
)
from tiannara.application.evolution.diversity import DiversityObserver
from tiannara.application.evolution.multi_generation_evolution import (
    MultiGenerationEvolutionCoordinator,
)

__all__ = [
    "CandidateSandbox",
    "CandidateGate",
    "CandidateVerdict",
    "CompiledCandidate",
    "BrokenTreeIntactInvariant",
    "EvolutionLedger",
    "EvolutionEvent",
    "EvolutionRecord",
    "EventType",
    "FitnessVector",
    "Gate",
    "GateContext",
    "GateResult",
    "PerformanceGate",
    "ProtectedInvariant",
    "SecurityGate",
    "RealBackendSandbox",
    "RepairedCandidate",
    "RunResult",
    "SelectionRecord",
    "TransitionRestoration",
    "TransitionRestorationOperator",
    "apply_restoration",
    "attempt_repair_cycle",
    "compute_fitness",
    "docker_available",
    "hash_artifact",
    "hash_run",
    "stable_isr_hash",
    "CompetitiveEvolutionCoordinator",
    "DeterministicComplexityPreference",
    "EliteAdvancementStrategy",
    "EMPTY_DELTA",
    "EvolutionEvent",
    "EventType",
    "MutationCandidate",
    "MutationOperator",
    "ISRDelta",
    "NullMutation",
    "SelectionDecision",
    "SelectionStrategy",
    "pareto_frontier",
    "score_candidate",
    "ActionInjectionOperator",
    "AwaitingSurfaceIntactInvariant",
    "ConstructiveVariationOperator",
    "CrossoverOperator",
    "FSMRepairVariation",
    "GuardRelaxationOperator",
    "NullCrossover",
    "RandomFSMExploration",
    "TestDeletionMutation",
    "AutonomousRepairCoordinator",
    "AutonomousRepairResult",
    "DiversityMetrics",
    "DiversityObserver",
    "EvolutionState",
    "GenerationState",
    "PopulationSnapshot",
    "TerminationReason",
    "MultiGenerationEvolutionCoordinator",
    "derive_evolution_id",
    "derive_generation_id",
]
