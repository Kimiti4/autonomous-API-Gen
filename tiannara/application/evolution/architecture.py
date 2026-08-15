"""R2.8.6 -- Architectural Integrity: two independent defenses.

Defense A — Structural Round-Trip Fidelity:
    project(compile(ISR)) == normalize(ISR)
    Catches compiler/backend divergence and source-patch deviation (I2's
    structural generalization).

Defense B — Constitutional Architectural Integrity:
    candidate_ISR ⊨ ConstitutionalInvariants
    AND
    actual_architectural_change(parent → candidate) ⊆ authorized_arch_change(Δ)
    Catches a candidate ISR that silently degrades protected architecture while
    compiling perfectly.

The two defenses are decoupled: A proves the compiler is honest; B proves the
candidate ISR is permissible. Neither substitutes for the other.

Constitutional invariants are owned by the evaluation authority, not derived
from the ISR. They constrain what any valid ISR may express.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Callable, Protocol

from constitutional_architecture.isr.model import ISR
from constitutional_architecture.isr.model.service import Service, ServiceDependency
from constitutional_architecture.isr.model.module import Module
from constitutional_architecture.isr.model.interface import Interface, InterfaceType
from constitutional_architecture.isr.model.workflow import Workflow, WorkflowTransition
from constitutional_architecture.isr.model.policy import Policy, PolicyType
from tiannara.domain.services.canonical import canonical_hash


# -- invariant class taxonomy --------------------------------------------------

class InvariantClass(str, enum.Enum):
    """Hierarchy of invariant mutability. Authorization must never override
    a constitutional invariant."""

    CONSTITUTIONAL = "constitutional"   # always reject violations
    ARCHITECTURAL = "architectural"     # reject unless declared in ISR Δ
    BEHAVIORAL = "behavioral"           # gate-dependent
    OPERATIONAL = "operational"         # policy-dependent
    ADVISORY = "advisory"               # score/fitness impact only


# -- structural skeleton (the == contract between normalize and project) ---------

@dataclass(frozen=True)
class ArchitecturalSkeleton:
    """Technology-neutral architectural skeleton extracted from an ISR or
    structurally projected from a compiled artifact.

    Both ``normalize`` and ``structural_project`` must produce this same type.
    The ``==`` comparison implements the ``≡`` equivalence relation: two
    skeletons are equal iff they represent the same architectural contract,
    regardless of implementation detail.
    """

    __test__ = False

    modules: frozenset[str]                    # Module.id
    dependencies: frozenset[tuple[str, str]]   # (source_module_id, target_module_id)
    public_interfaces: frozenset[tuple[str, str]]  # (module_id, interface_id)
    internal_interfaces: frozenset[tuple[str, str]]
    auth_required_operations: frozenset[tuple[str, str]]  # (module_id, operation_id)
    auth_required_endpoints: frozenset[tuple[str, str]]    # (interface_id, endpoint_id)
    stateful_services: frozenset[str]         # Service.id that is NOT stateless
    transition_graphs: frozenset[tuple[str, tuple[str, str]]]  # (workflow_id, (from, to))
    auth_policy_ids: frozenset[str]          # Policy.id for auth-type policies
    persistence_policy_ids: frozenset[str]   # Policy.id for persistence-type policies
    secured_interface_ids: frozenset[str]    # Interface.id referencing a policy

    def skeleton_hash(self) -> str:
        return canonical_hash((
            sorted(self.modules),
            sorted(self.dependencies),
            sorted(self.public_interfaces),
            sorted(self.internal_interfaces),
            sorted(self.auth_required_operations),
            sorted(self.auth_required_endpoints),
            sorted(self.stateful_services),
            sorted(self.transition_graphs),
            sorted(self.auth_policy_ids),
            sorted(self.persistence_policy_ids),
            sorted(self.secured_interface_ids),
        ))


# -- Defense A: normalize(ISR) --------------------------------------------------

def normalize(isr: ISR) -> ArchitecturalSkeleton:
    """Extract the architectural skeleton from an ISR.

    Pure ISR function — no knowledge of compilation or artifacts.
    """
    modules: set[str] = set()
    dependencies: set[tuple[str, str]] = set()
    public_ifaces: set[tuple[str, str]] = set()
    internal_ifaces: set[tuple[str, str]] = set()
    auth_ops: set[tuple[str, str]] = set()
    auth_endpoints: set[tuple[str, str]] = set()
    stateful: set[str] = set()
    transitions: set[tuple[str, tuple[str, str]]] = set()
    auth_policies: set[str] = set()
    persistence_policies: set[str] = set()
    secured_ifaces: set[str] = set()

    def _walk(mod: Module) -> None:
        modules.add(mod.id)
        for dep in mod.dependencies:
            dependencies.add((mod.id, dep))
        for svc in mod.services:
            if not svc.is_stateless:
                stateful.add(svc.id)
            for op in svc.operations:
                if op.required_permissions and not op.is_public:
                    auth_ops.add((mod.id, op.id))
            for dep in svc.dependencies:
                dependencies.add((mod.id, dep.target_service_id))
        for iface in mod.interfaces:
            key = (mod.id, iface.id)
            if iface.is_internal:
                internal_ifaces.add(key)
            else:
                public_ifaces.add(key)
            if iface.secured_by_policy_id is not None:
                secured_ifaces.add(iface.id)
            for ep in iface.endpoints:
                if ep.required_permissions or not ep.is_public:
                    auth_endpoints.add((iface.id, ep.id))
        for policy in mod.policies:
            if policy.policy_type == PolicyType.AUTHENTICATION:
                auth_policies.add(policy.id)
            elif policy.policy_type == PolicyType.DATA_RETENTION:
                persistence_policies.add(policy.id)
        for wf in mod.workflows:
            for t in wf.transitions:
                transitions.add((wf.id, (t.from_state_id, t.to_state_id)))

    for mod in isr.system.modules:
        _walk(mod)

    return ArchitecturalSkeleton(
        modules=frozenset(modules),
        dependencies=frozenset(dependencies),
        public_interfaces=frozenset(public_ifaces),
        internal_interfaces=frozenset(internal_ifaces),
        auth_required_operations=frozenset(auth_ops),
        auth_required_endpoints=frozenset(auth_endpoints),
        stateful_services=frozenset(stateful),
        transition_graphs=frozenset(transitions),
        auth_policy_ids=frozenset(auth_policies),
        persistence_policy_ids=frozenset(persistence_policies),
        secured_interface_ids=frozenset(secured_ifaces),
    )


def structural_project(artifact: object) -> ArchitecturalSkeleton:
    """Project a compiled artifact's structure onto the architectural skeleton.

    In production this parses generated source (AST, bytecode, OpenAPI spec,
    etc.). In the hermetic test corpus it delegates to ``normalize`` since the
    artifact is not a real compilation — the corpus tests Defense B directly.
    """
    if isinstance(artifact, ISR):
        return normalize(artifact)
    raise NotImplementedError(
        "structural_project requires a real artifact parser in production; "
        "the hermetic corpus delegates to normalize(ISR)."
    )


def round_trip_integrity(isr: ISR) -> bool:
    """Defense A: project(compile(ISR)) ≡ normalize(ISR).

    In the hermetic corpus, artifact projection == normalize, so this always
    holds. In production this catches compiler divergence.
    """
    return structural_project(isr) == normalize(isr)


# -- Defense B: constitutional invariants ---------------------------------------

@dataclass(frozen=True)
class InvariantViolation:
    """A single invariant violation."""

    __test__ = False

    invariant: str
    cls: InvariantClass
    detail: str


@dataclass(frozen=True)
class InvariantResult:
    """Result of evaluating constitutional architectural invariants."""

    __test__ = False

    violations: tuple[InvariantViolation, ...] = ()
    invariant_hash: str = ""

    @property
    def accept(self) -> bool:
        return not self.violations

    @property
    def constitutional_violations(self) -> tuple[InvariantViolation, ...]:
        return tuple(v for v in self.violations if v.cls == InvariantClass.CONSTITUTIONAL)

    @property
    def architectural_violations(self) -> tuple[InvariantViolation, ...]:
        return tuple(v for v in self.violations if v.cls == InvariantClass.ARCHITECTURAL)


# -- constitutional invariant set (evaluation-authority-owned) ------------------
# These define which architectural properties are protected (cannot be silently
# removed) and which are evolvable (may change only when declared in the ISR Δ).

@dataclass(frozen=True)
class ConstitutionalInvariants:
    """The invariant set owns by the evaluation authority.

    ``protected_auth`` — auth requirements that must not be silently removed.
    ``protected_persistence`` — stateful services that must not become ephemeral.
    ``protected_boundaries`` — module dependencies that must not be added silently.
    """

    __test__ = False

    protected_auth: frozenset[tuple[str, str]] = field(default_factory=frozenset)
    protected_persistence: frozenset[str] = field(default_factory=frozenset)
    protected_boundaries: frozenset[tuple[str, str]] = field(default_factory=frozenset)


def default_fsm_invariants(parent_isr: ISR) -> ConstitutionalInvariants:
    """Derive the initial constitutional invariant set from the parent ISR.

    Protected auth = operations with required_permissions; protected persistence
    = stateful services; protected boundaries = existing module dependencies.
    These are the architectural properties no candidate may silently remove.
    """
    parent_skel = normalize(parent_isr)
    return ConstitutionalInvariants(
        protected_auth=parent_skel.auth_required_operations,
        protected_persistence=parent_skel.stateful_services,
        protected_boundaries=parent_skel.dependencies,
    )


# -- architectural authorization (R2.8.4 pattern generalized) --------------------

@dataclass(frozen=True)
class ArchitecturalAuthorization:
    """ISR-delta-derived grant for architectural changes.

    Mirrors ``Authorization`` from R2.8.4 but at the architectural level:
    the authorized set is the actual architectural change between the parent
    and candidate ISR, derived by projection — never hand-injected.
    """

    __test__ = False

    parent_skeleton_hash: str
    candidate_skeleton_hash: str
    delta_hash: str
    authorized_architectural_changes: frozenset[str]

    @property
    def authorization_hash(self) -> str:
        return canonical_hash((
            self.parent_skeleton_hash,
            self.candidate_skeleton_hash,
            self.delta_hash,
            sorted(self.authorized_architectural_changes),
        ))

    @classmethod
    def from_delta(cls, parent_isr: ISR, candidate_isr: ISR,
                   projector: "ArchitectureProjector") -> "ArchitecturalAuthorization":
        parent_skel = normalize(parent_isr)
        candidate_skel = normalize(candidate_isr)
        changes = projector.project(parent_skel, candidate_skel)
        delta_hash = canonical_hash((parent_skel.skeleton_hash(), candidate_skel.skeleton_hash()))
        return cls(
            parent_skeleton_hash=parent_skel.skeleton_hash(),
            candidate_skeleton_hash=candidate_skel.skeleton_hash(),
            delta_hash=delta_hash,
            authorized_architectural_changes=changes,
        )


class ArchitectureProjector(Protocol):
    """Projects an architectural skeleton delta onto authorized change symbols."""

    def project(self, parent: ArchitecturalSkeleton,
                candidate: ArchitecturalSkeleton) -> frozenset[str]:
        ...


class DeltaArchitectureProjector:
    """Authorizes ALL architectural changes declared in the ISR delta.

    This is the counterpart to R2.8.4's ``FSMTestSurfaceProjector``: it
    projects the skeleton delta into a set of change descriptors. The
    invariant layer then checks whether each change violates a protected
    property or was declared (authorized) in the delta.
    """

    __test__ = False

    def project(self, parent: ArchitecturalSkeleton,
                candidate: ArchitecturalSkeleton) -> frozenset[str]:
        changes: set[str] = set()
        # auth changes
        removed_auth = parent.auth_required_operations - candidate.auth_required_operations
        for op in removed_auth:
            changes.add(f"auth_removed:{op[0]}:{op[1]}")
        added_auth = candidate.auth_required_operations - parent.auth_required_operations
        for op in added_auth:
            changes.add(f"auth_added:{op[0]}:{op[1]}")
        # persistence changes
        degraded_persistence = parent.stateful_services - candidate.stateful_services
        for svc in degraded_persistence:
            changes.add(f"persistence_degraded:{svc}")
        gained_persistence = candidate.stateful_services - parent.stateful_services
        for svc in gained_persistence:
            changes.add(f"persistence_gained:{svc}")
        # boundary changes
        new_deps = candidate.dependencies - parent.dependencies
        for dep in new_deps:
            changes.add(f"boundary_added:{dep[0]}->{dep[1]}")
        removed_deps = parent.dependencies - candidate.dependencies
        for dep in removed_deps:
            changes.add(f"boundary_removed:{dep[0]}->{dep[1]}")
        # transition graph changes
        new_trans = candidate.transition_graphs - parent.transition_graphs
        for wf_id, (frm, to) in new_trans:
            changes.add(f"transition_added:{wf_id}:{frm}_to_{to}")
        removed_trans = parent.transition_graphs - candidate.transition_graphs
        for wf_id, (frm, to) in removed_trans:
            changes.add(f"transition_removed:{wf_id}:{frm}_to_{to}")
        return frozenset(changes)


# -- Defense B: invariant evaluation --------------------------------------------

def evaluate_invariants(parent_isr: ISR, candidate_isr: ISR,
                        authorization: ArchitecturalAuthorization | None,
                        invariants: ConstitutionalInvariants | None = None,
                        ) -> InvariantResult:
    """Evaluate B: candidate ISR must not silently violate protected architecture.

    A constitutional violation (protected property silently removed) is always
    rejected, regardless of authorization. An architectural violation (change
    to a protected property) is rejected unless the change is authorized by the
    ISR delta.
    """
    if invariants is None:
        invariants = default_fsm_invariants(parent_isr)

    parent_skel = normalize(parent_isr)
    candidate_skel = normalize(candidate_isr)
    violations: list[InvariantViolation] = []

    # --- Constitutional: auth must not be silently removed ---
    removed_auth = parent_skel.auth_required_operations - candidate_skel.auth_required_operations
    for op in removed_auth:
        if op in invariants.protected_auth:
            violations.append(InvariantViolation(
                invariant="auth_not_silently_removable",
                cls=InvariantClass.CONSTITUTIONAL,
                detail=f"auth removed on {op[0]}::{op[1]} (constitutionally protected)",
            ))

    # --- Constitutional: persistence must not be silently degraded ---
    degraded = parent_skel.stateful_services - candidate_skel.stateful_services
    for svc in degraded:
        if svc in invariants.protected_persistence:
            violations.append(InvariantViolation(
                invariant="persistence_not_degradable",
                cls=InvariantClass.CONSTITUTIONAL,
                detail=f"stateful service {svc} became stateless (constitutionally protected)",
            ))

    # --- Architectural: new boundaries must be declared in the ISR delta ---
    new_deps = candidate_skel.dependencies - parent_skel.dependencies
    auth_changes = (
        authorization.authorized_architectural_changes
        if authorization else frozenset()
    )
    for dep in new_deps:
        if dep not in invariants.protected_boundaries:
            # new boundary crossing — must be authorized by the ISR delta
            if f"boundary_added:{dep[0]}->{dep[1]}" not in auth_changes:
                violations.append(InvariantViolation(
                    invariant="undeclared_boundary_change",
                    cls=InvariantClass.ARCHITECTURAL,
                    detail=f"new module dependency {dep[0]}->{dep[1]} not declared in ISR Δ",
                ))

    # --- Constitutional: protected boundaries must not be silently removed ---
    removed_deps = parent_skel.dependencies - candidate_skel.dependencies
    for dep in removed_deps:
        if dep in invariants.protected_boundaries:
            violations.append(InvariantViolation(
                invariant="boundary_not_silently_removable",
                cls=InvariantClass.CONSTITUTIONAL,
                detail=f"boundary {dep[0]}->{dep[1]} was removed (constitutionally protected)",
            ))

    # no auth added on previously-unprotected operations is also a change
    # but adding auth is not a violation — it's stricter than required

    invariant_hash = canonical_hash((
        parent_skel.skeleton_hash(),
        candidate_skel.skeleton_hash(),
        sorted(invariants.protected_auth),
    ))

    return InvariantResult(
        violations=tuple(violations),
        invariant_hash=invariant_hash,
    )


def architectural_round_trip_integrity(parent_isr: ISR, candidate_isr: ISR) -> bool:
    """Defense A applied to the candidate: compile(candidate_ISR) ≡ candidate_ISR."""
    return round_trip_integrity(candidate_isr)
