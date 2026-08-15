import datetime as dt
import enum
import uuid
from typing import Any
from pydantic import BaseModel, ConfigDict, Field, model_validator
from .fitness import FitnessVector
from ..services.canonical import canonical_hash


class GateStatus(str, enum.Enum):
    PASS = "pass"
    FAIL = "fail"
    NOT_EVALUATED = "not_evaluated"


class GateResult(BaseModel):
    gate: str
    status: GateStatus
    detail: str = ""


# -- R2.7: precise regression substrate ---------------------------------------

class TestOutcome(str, enum.Enum):
    """Normalized per-test outcome across backends (pytest, go test, ...)."""

    __test__ = False  # pytest: not a test class

    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"


class TestExecution(BaseModel):
    """A single test's normalized outcome for one run attempt.

    Identity is two-layered (R2.7 sharpenings):
      * ``test_id``  -- the backend node id (e.g. pytest ``path::test_name``).
        Survives deletion/rename only as a *name*; rename is a distinct signal.
      * ``content_hash`` -- SHA-256 over the test's body+assertions read from the
        materialized tree. Same name with a different body is *gutting*
        (an assertion removed while the test still green-lights green).
    ``flaky`` is set when a test's outcome varied across infra-retry attempts
    inside a single run -- a deception vector R2.7 attributes instead of masking.
    """

    __test__ = False

    test_id: str
    outcome: TestOutcome
    duration_seconds: float = 0.0
    content_hash: str = ""
    attempt: int = 0
    flaky: bool = False

    def content_identity(self) -> str:
        """Identity key used by the regression comparator (name + body)."""
        return f"{self.test_id}@{self.content_hash}"


class Baseline(BaseModel):
    """Immutable, content-hash pinned snapshot of a passing test surface.

    Frozen so a candidate can never rewrite the baseline it is compared
    against: it is pinned once per selection round and every candidate is
    compared against it, never allowed to rewrite it.
    """

    __test__ = False

    model_config = ConfigDict(frozen=True)

    baseline_id: str
    created_at: dt.datetime = Field(
        default_factory=lambda: dt.datetime.now(dt.UTC)
    )
    environment_fingerprint: str = ""
    tests: tuple[TestExecution, ...]
    content_hash: str = ""

    @classmethod
    def from_run(
        cls,
        run_tests: "tuple[TestExecution, ...]",
        environment_fingerprint: str = "",
        baseline_id: str | None = None,
        now: dt.datetime | None = None,
    ) -> "Baseline":
        return cls(
            baseline_id=baseline_id or f"baseline-{uuid.uuid4()}",
            created_at=now or dt.datetime.now(dt.UTC),
            environment_fingerprint=environment_fingerprint,
            tests=run_tests,
            content_hash=canonical_hash(
                {"tests": [t.content_identity() for t in run_tests]}
            ),
        )


class RegressionClass(str, enum.Enum):
    """Precise per-test classification of a candidate vs its baseline.

    Reject-by-default is the R2.7 rule: a candidate that *looks* better but
    regressed, removed a test, skipped one, flaked, or gutted an assertion is
    REJECTED unless an explicit protection opts it in.
    """

    __test__ = False

    NEW_PASS = "new_pass"
    PRESERVED_PASS = "preserved_pass"
    RESOLVED_FAILURE = "resolved_failure"
    NEW_FAILURE = "new_failure"
    REGRESSED_FAILURE = "regressed_failure"
    PERSISTING_FAILURE = "persisting_failure"
    NEW_ERROR = "new_error"
    REMOVED_TEST = "removed_test"
    NEW_SKIP = "new_skip"
    FLAKE = "flake"
    CONTENT_GUTTING = "content_gutting"


#: Classes that reject the candidate by default. PRESERVED_PASS, NEW_PASS and
#: RESOLVED_FAILURE are the only non-reject classes -- everything else is a
#: regression, a disappearance, or a non-determinism signal.
REGRESSION_REJECT_CLASSES = frozenset({
    RegressionClass.NEW_FAILURE,
    RegressionClass.REGRESSED_FAILURE,
    RegressionClass.PERSISTING_FAILURE,
    RegressionClass.NEW_ERROR,
    RegressionClass.REMOVED_TEST,
    RegressionClass.NEW_SKIP,
    RegressionClass.FLAKE,
    RegressionClass.CONTENT_GUTTING,
})


class RegressionResult(BaseModel):
    """Output of R2.7's set-difference regression comparison.

    ``class_counts`` records how many tests landed in each RegressionClass;
    the named tuples are the test_ids driving each reject-class so auditors can
    see exactly why a candidate was refused (architectural reasoning stays
    transparent even for hidden-test / gutting rejections).
    """

    __test__ = False

    model_config = ConfigDict(frozen=True)

    baseline_id: str
    class_counts: dict[str, int] = Field(default_factory=dict)
    regressed: tuple[str, ...] = ()
    newly_failing: tuple[str, ...] = ()
    persisting: tuple[str, ...] = ()
    newly_added: tuple[str, ...] = ()
    vanished: tuple[str, ...] = ()
    flake: tuple[str, ...] = ()
    gutting: tuple[str, ...] = ()
    accept: bool = True
    precision: str = "per_test"
    detail: str = ""

    @property
    def regressed_count(self) -> int:
        return self.class_counts.get(RegressionClass.REGRESSED_FAILURE.value, 0) + \
            self.class_counts.get(RegressionClass.NEW_FAILURE.value, 0)


# -- R2.7.5: fitness capability model -----------------------------------------

class DimensionStatus(str, enum.Enum):
    """Epistemic state of a fitness dimension.

    ``unevaluated`` (no evaluator ran / capability absent) is NOT ``failed``
    (an evaluator ran and the software failed it). Conflating the two is the
    dangerous epistemic error R2.7.5 makes unrepresentable.
    """

    EVALUATED = "evaluated"
    UNEVALUATED = "unevaluated"
    FAILED = "failed"

    __test__ = False


class DimensionAvailability(str, enum.Enum):
    """Whether a fitness dimension's evaluator is available to Tiannara."""

    AVAILABLE = "available"
    STUB = "stub"
    UNAVAILABLE = "unavailable"

    __test__ = False


class DimensionResult(BaseModel):
    """A single fitness dimension's outcome with explicit availability.

    ``score`` is 0.0 when unevaluated/unavailable -- but the accompanying
    ``status``/``availability`` encode *why*, so an unknown result is never
    mistaken for a failed result. Backwards-compatible with R2.6's
    ``FitnessVector`` (which remains the Pareto-scoring view); this carries the
    capability/attribution metadata R2.8 promotes into scoring.
    """

    __test__ = False

    name: str
    score: float
    status: DimensionStatus
    availability: DimensionAvailability
    evaluator: str
    evidence: dict[str, Any] = Field(default_factory=dict)

    @property
    def is_unknown(self) -> bool:
        """True iff the dimension was not evaluated (capability absent/stub)."""
        return self.status == DimensionStatus.UNEVALUATED or (
            self.availability == DimensionAvailability.UNAVAILABLE
            and self.status != DimensionStatus.FAILED
        )

    @property
    def is_failure(self) -> bool:
        """True iff an evaluator ran and the software failed it."""
        return self.status == DimensionStatus.FAILED


# -- R2.7.5-G: evaluation trust boundary ---------------------------------------

class Visibility(str, enum.Enum):
    """Whether the evolution process may *observe* a test.

    Independent axis from ``protected`` (what evolution may *modify*):
      visibility = what you can see         (observation authority)
      protected  = what you can change       (mutation authority)
    """

    VISIBLE = "visible"
    HIDDEN = "hidden"

    __test__ = False


class Provenance(str, enum.Enum):
    """Who created a test identity -- the privilege axis for protection.

    Only the privileged evaluation authority may mint
    ``EVALUATION_AUTHORITY`` identities (the protected ground-truth / holdout
    core). Mutation operators mint ``ISR_GENERATED`` identities, which are by
    definition *not* protected. This is the mechanism that makes "protection is
    a privilege the engine cannot grant itself" structurally true.
    """

    EVALUATION_AUTHORITY = "evaluation_authority"
    ISR_GENERATED = "isr_generated"

    __test__ = False


class TestIdentity(BaseModel):
    """Identity + policy envelope for a single test in the evaluation surface.

    ``protected`` is derived from ``provenance`` (see ``Provenance``) and enforced
    here: an ``EVALUATION_AUTHORITY`` test is protected; an ``ISR_GENERATED``
    test is not. The ``evolvable + hidden`` quadrant is disallowed by
    construction -- a hidden test that evolution cannot see must still be
    protected (holdout ground truth), never evolvable.
    """

    __test__ = False

    test_id: str
    content_hash: str = ""
    protected: bool = False
    visibility: Visibility = Visibility.VISIBLE
    provenance: Provenance = Provenance.ISR_GENERATED
    anchor_event_id: str = ""

    @classmethod
    def from_provenance(
        cls,
        test_id: str,
        provenance: Provenance,
        *,
        content_hash: str = "",
        visibility: Visibility = Visibility.VISIBLE,
        anchor_event_id: str = "",
    ) -> "TestIdentity":
        return cls(
            test_id=test_id,
            content_hash=content_hash,
            protected=(provenance == Provenance.EVALUATION_AUTHORITY),
            visibility=visibility,
            provenance=provenance,
            anchor_event_id=anchor_event_id,
        )

    @model_validator(mode="after")
    def _enforce_protection_quadrants(self) -> "TestIdentity":
        expected_protected = self.provenance == Provenance.EVALUATION_AUTHORITY
        if self.protected != expected_protected:
            raise ValueError(
                f"protected must be {expected_protected} for "
                f"provenance={self.provenance.value} "
                "(protection is granted only from evaluation-authority provenance)"
            )
        if not self.protected and self.visibility == Visibility.HIDDEN:
            raise ValueError(
                "evolvable + hidden tests are disallowed: holdout tests must be "
                "protected (see R2.7.5-G)"
            )
        return self

    def is_protected(self) -> bool:
        return self.protected

    def is_hidden(self) -> bool:
        return self.visibility == Visibility.HIDDEN


class DriftClass(str, enum.Enum):
    """Outcome of comparing a test's identity against its protected/evolvable policy."""

    PRESERVED = "preserved"            # content unchanged
    CONTENT_GUTTING = "content_gutting"  # protected test body altered -> reject
    REMOVED_TEST = "removed_test"      # protected test vanished -> reject
    HIDDEN_LEAK = "hidden_leak"        # evolution saw a hidden test -> reject
    REQUIRES_JUSTIFICATION = "requires_justification"  # evolvable drift, not yet explained
    ALLOWED_DRIFT = "allowed_drift"    # evolvable drift with causal justification

    __test__ = False


class DriftResult(BaseModel):
    """R2.7.5-G drift-classification output (policy-driven, not just hashing).

    Reject classes are reject-by-default; evolvable drift is *flagged* for
    causal justification rather than auto-rejected, so a legitimate repair that
    adjusts a derived test is not blocked.
    """

    __test__ = False

    protected_rejected: tuple[str, ...] = ()
    removed: tuple[str, ...] = ()
    hidden_leaks: tuple[str, ...] = ()
    requires_justification: tuple[str, ...] = ()
    allowed_drift: tuple[str, ...] = ()
    preserved: tuple[str, ...] = ()
    accept: bool = True
    detail: str = ""

    def reject_reasons(self) -> dict[str, tuple[str, ...]]:
        return {
            DriftClass.CONTENT_GUTTING.value: self.protected_rejected,
            DriftClass.REMOVED_TEST.value: self.removed,
            DriftClass.HIDDEN_LEAK.value: self.hidden_leaks,
        }


class DimensionPolicy(BaseModel):
    """Declared policy for a fitness dimension (R2.8.1 review point #3).

    Makes the critical/advisory and implemented/unimplemented distinctions
    explicit so an *unevaluated* dimension is never silently treated as a pass
    -- the central epistemic safety property the adversarial phase depends on:

      * ``critical``         -- if an evaluator runs, the candidate must pass it.
      * ``implemented``      -- is a real evaluator wired for this dimension?
        When False, an unevaluated result is transitional "capability absent"
        (allowed in R2.7.5, but recorded as such -- never a silent pass).
      * ``when_unevaluated`` -- policy once the evaluator IS implemented:
        ``"infeasible"`` (critical; reject) or ``"allow"`` (advisory).
    """

    __test__ = False

    name: str
    critical: bool = True
    implemented: bool = False
    evaluator: str = ""
    availability: DimensionAvailability = DimensionAvailability.UNAVAILABLE
    when_unevaluated: str = "infeasible"  # "infeasible" | "allow"

    def unevaluated_is_infeasible(self) -> bool:
        """True iff an unevaluated result for this dimension must reject.

        An *unimplemented* capability is transitional: it is allowed (R2.7.5)
        but the policy still declares the dimension ``critical`` so that once the
        evaluator lands (R2.8.5/8.6), unevaluated immediately becomes infeasible.
        """
        if not self.implemented:
            return False
        return self.critical and self.when_unevaluated == "infeasible"

    def to_dimension_result(self, status: DimensionStatus = DimensionStatus.UNEVALUATED,
                            score: float = 0.0, evidence: dict | None = None) -> DimensionResult:
        return DimensionResult(
            name=self.name, score=score, status=status,
            availability=self.availability, evaluator=self.evaluator,
            evidence=evidence or {},
        )


# -- runtime evidence ----------------------------------------------------------

class TestRunResult(BaseModel):
    __test__ = False  # not a pytest test class (pydantic model named Test*)

    passed: bool
    exit_code: int
    total_tests: int = 0
    failed_tests: int = 0
    duration_seconds: float = 0.0
    logs_path: str | None = None
    # R2.7: normalized per-test outcomes emitted by the backend adapter.
    # Defaults to () so every existing aggregate-only consumer (R2.3-R2.6) is
    # undisturbed; the regression gate uses these when present and otherwise
    # degrades to the pass-count comparison.
    tests: tuple[TestExecution, ...] = ()

    @property
    def pass_rate(self) -> float:
        if self.total_tests == 0:
            return 0.0
        return (self.total_tests - self.failed_tests) / self.total_tests

    @property
    def pass_count(self) -> int:
        """Number of tests that passed (used by the R2.4 regression assertion and
        as the R2.6 aggregate fallback when per-test outcomes are unavailable)."""
        return self.total_tests - self.failed_tests

    def baseline(self, environment_fingerprint: str = "",
                 baseline_id: str | None = None) -> Baseline:
        """Pin this run as an immutable R2.7 regression baseline."""
        return Baseline.from_run(
            self.tests,
            environment_fingerprint=environment_fingerprint,
            baseline_id=baseline_id,
        )


class Verdict(str, enum.Enum):
    PASS = "pass"
    FAIL = "fail"
    QUARANTINED = "quarantined"


class CertificationEvidence(BaseModel):
    """Tamper-evident record bound to ISR provenance.

    Appended to the EvidenceLedger with a SHA-256 hash chain.
    """

    evidence_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str
    created_at: dt.datetime = Field(default_factory=lambda: dt.datetime.now(dt.UTC))
    isr_hash: str
    genome_id: str
    backend_name: str
    compilation_success: bool
    test_run: TestRunResult | None = None
    security_scan_performed: bool = False
    security_vulnerabilities: int = 0
    fitness: FitnessVector = Field(default_factory=FitnessVector)
    gate_results: list[GateResult] = Field(default_factory=list)
    verdict: Verdict = Verdict.FAIL
    error: str | None = None
    previous_hash: str | None = None
    record_hash: str | None = None
