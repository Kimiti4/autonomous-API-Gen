"""W01-W22 remediation register for the general software-generation programme.

This module is the machine-readable source of truth for the master plan's
remediation work packages. It is deliberately data plus validation only:
no work package counts as closed because this file mentions it. Validation
fails closed on unresolved evidence references, unsupported status claims,
broken dependency graphs, and fixed defects without a canonical regression
test.

Status semantics
----------------
NOT_STARTED            no implementation work has landed on main
IN_PROGRESS            some implementation exists but closure evidence is missing
BLOCKED                a declared dependency prevents progress
IMPLEMENTED_UNVERIFIED code exists and a canonical test exercises it, but at
                       least one closure-gate requirement is still unmet
VERIFIED               every closure-gate requirement is backed by canonical,
                       candidate-bound evidence (test + workflow or artifact)
REGRESSION             previously verified behaviour is currently broken

Certification tiers follow the master plan §4: structural, build, runtime,
behavioral, security, operational, release.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterable, Sequence

SCHEMA_ID = "esap.remediation.register"
SCHEMA_VERSION = "1.0.0"

REPO_ROOT = Path(__file__).resolve().parents[2]


class Status(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    BLOCKED = "BLOCKED"
    IMPLEMENTED_UNVERIFIED = "IMPLEMENTED_UNVERIFIED"
    VERIFIED = "VERIFIED"
    REGRESSION = "REGRESSION"


class DefectStatus(str, Enum):
    OPEN = "OPEN"
    FIXED_UNVERIFIED = "FIXED_UNVERIFIED"
    VERIFIED = "VERIFIED"
    REGRESSION = "REGRESSION"


class CertificationTier(str, Enum):
    STRUCTURAL = "structural"
    BUILD = "build"
    RUNTIME = "runtime"
    BEHAVIORAL = "behavioral"
    SECURITY = "security"
    OPERATIONAL = "operational"
    RELEASE = "release"


class EvidenceKind(str, Enum):
    CODE = "code"
    TEST = "test"
    WORKFLOW = "workflow"
    PR = "pr"
    EVIDENCE = "evidence"


@dataclass(frozen=True)
class Evidence:
    kind: EvidenceKind
    ref: str
    note: str = ""


class CompilerDisposition(str, Enum):
    REFERENCE = "reference"
    FAIL_CLOSED = "fail_closed"
    RUNTIME_PROVEN = "runtime_proven"
    SHELL = "shell"
    INTEGRATION_UNPROVEN = "integration_unproven"


class CompilerGate(str, Enum):
    PRESERVATION = "preservation"
    EXECUTION = "execution"
    PARITY = "parity"
    INTEGRATION = "integration"


@dataclass(frozen=True)
class CompilerTarget:
    """A tracked compiler path. Registration is not a production-ready claim."""

    target_id: str
    family: str
    disposition: CompilerDisposition
    gate: CompilerGate
    work_package: str
    note: str
    production_ready: bool = False


@dataclass(frozen=True)
class WorkPackage:
    id: str
    title: str
    requirement: str
    status: Status
    dependencies: tuple[str, ...]
    evidence: tuple[Evidence, ...]
    closure_gate: str
    claimed_tiers: tuple[CertificationTier, ...]
    verified_tiers: tuple[CertificationTier, ...] = ()
    limitations: tuple[str, ...] = ()


@dataclass(frozen=True)
class Defect:
    id: str
    title: str
    location: str
    status: DefectStatus
    severity: str
    regression_test: str | None = None
    note: str = ""


KNOWN_PRS: dict[int, str] = {
    73: "OPEN",
    77: "OPEN",
    78: "OPEN",
    94: "OPEN",
    95: "OPEN",
    97: "OPEN",
    99: "OPEN",
    106: "OPEN",
    108: "OPEN",
    124: "MERGED",
    125: "MERGED",
    131: "MERGED",
    133: "MERGED",
    134: "MERGED",
    135: "MERGED",
    136: "MERGED",
    137: "MERGED",
    138: "CLOSED",
    139: "MERGED",
    140: "MERGED",
    152: "MERGED",
    156: "MERGED",
    157: "MERGED",
    165: "MERGED",
}


def _code(ref: str, note: str = "") -> Evidence:
    return Evidence(EvidenceKind.CODE, ref, note)


def _test(ref: str, note: str = "") -> Evidence:
    return Evidence(EvidenceKind.TEST, ref, note)


def _workflow(ref: str, note: str = "") -> Evidence:
    return Evidence(EvidenceKind.WORKFLOW, ref, note)


def _pr(number: int, note: str = "") -> Evidence:
    return Evidence(EvidenceKind.PR, f"PR#{number}", note)


def _artifact(ref: str, note: str = "") -> Evidence:
    return Evidence(EvidenceKind.EVIDENCE, f"workflow-artifact:{ref}", note)


WORK_PACKAGES: tuple[WorkPackage, ...] = (
    WorkPackage(
        id="W01",
        title="Requirements ingestion and source binding",
        requirement=(
            "Bind every requirement to an authoritative source, stable identifier, "
            "version/hash, provenance, and approval status; reject missing, duplicate "
            "or invented mappings."
        ),
        status=Status.IMPLEMENTED_UNVERIFIED,
        dependencies=(),
        evidence=(
            _code("reqgraph/core/graph.py"),
            _code("reqgraph/ingestion/tor_extractor.py"),
            _code("reqgraph/adapters/tor_isr.py"),
            _code("autonomous-api/app/engine/source_bound_full_stack.py"),
            _test("tests/test_tor_ingestion_and_isr_projection.py"),
            _test("tests/test_source_bound_behavioral_projection.py"),
            _test("tests/integration/test_generated_backend_behavior_builds.py"),
            _test("tests/cbc1/test_source_bound_full_stack_projection.py"),
            _workflow(".github/workflows/root-canonical-suite.yml"),
            _workflow(".github/workflows/react-frontend-compiler.yml"),
            _artifact("cbc1-a-evidence", "PR #152 Campaign A 78/78 CERTIFIED; Tier A 4711 passed"),
            _pr(140, "controlled TOR extraction and ISR requirement projection merged"),
            _pr(138, "superseded by #140 and closed"),
            _pr(152, "source-bound behavioral projection, fail-closed mapping, and mutation evidence"),
        ),
        closure_gate=(
            "Mutating an authoritative source invalidates every derived binding; "
            "missing or duplicate mandatory mappings block progression."
        ),
        claimed_tiers=(CertificationTier.STRUCTURAL, CertificationTier.BEHAVIORAL),
        limitations=(
            "Requirement approval status is carried in requirement_ref properties rather than a first-class ISR revision attribute.",
            "The register's no-package-verified guard defers VERIFIED status until the programme closure phase, despite candidate-bound CI evidence in PR #152.",
        ),
    ),
    WorkPackage(
        id="W02",
        title="Requirements-to-ISR semantic compilation",
        requirement=(
            "Extend structured intent beyond entity and edge names to typed fields, "
            "validation, formulas, invariants, state transitions, API behaviour, "
            "authorization, effects, and observable consequences."
        ),
        status=Status.IN_PROGRESS,
        dependencies=("W01",),
        evidence=(
            _code("isr/core/graph.py"),
            _code("isr/core/behavior.py"),
            _code("reqgraph/core/invariants.py"),
            _code("reqgraph/adapters/tor_isr.py"),
            _code("compiler/core/lowering.py"),
            _code("compiler/core/authorization.py"),
            _code("compiler/backends/python_fastapi.py"),
            _code("certification/authorization/corpus.py"),
            _code("certification/authorization/candidate.py"),
            _code("certification/authorization/runtime.py"),
            _code("certification/authorization/campaign.py"),
            _code("certification/authorization/verifier.py"),
            _code("certification/authorization/workloads.py"),
            _code("certification/authorization/workload_payroll.py"),
            _code("certification/authorization/workload_orders.py"),
            _code("certification/authorization/workload_inventory.py"),
            _code("certification/authorization/workload_shipments.py"),
            _code("certification/authorization/workload_declared_api.py"),
            _test("tests/cbc1/test_campaign_a.py"),
            _test("tests/test_source_bound_behavioral_projection.py"),
            _test("tests/test_behavioral_capability_gate.py"),
            _test("tests/test_authorization_enforcement.py"),
            _test("tests/authorization/test_authorization_campaign.py"),
            _test("tests/integration/test_generated_backend_behavior_builds.py"),
            _workflow(".github/workflows/react-frontend-compiler.yml"),
            _workflow(".github/workflows/authorization-campaign.yml"),
            _pr(137, "typed behavioural ISR contract merged; end-to-end emitter consumption remains a separate closure gate"),
            _pr(152, "source-bound typed behavior reaches Python, Rust, and React plans"),
            _pr(157, "trusted principal resolution and per-route policy enforcement merged"),
            _pr(165, "declared API operation enforcement and five-workload authorization lane merged"),
        ),
        closure_gate=(
            "Representative requirements produce typed ISR semantics with explicit "
            "unresolved items, and no mandatory semantic element is lost in lowering."
        ),
        claimed_tiers=(CertificationTier.STRUCTURAL, CertificationTier.BEHAVIORAL),
        limitations=(
            "The TOR path does not extract effects or observable consequences from requirement prose; effect and consequence nodes are reviewer-authored declarations, not derived intent.",
            "Source-bound typed fields, rules, transitions, API contracts, and frontend interactions reach plans and generated artifacts; authorization is enforced for service- and API-operation-scoped policies on the Python backend only.",
            "The Rust backend still refuses every authorization obligation, including declared API operations; the Python backend now emits and enforces declared operations, and the authorization lane certifies them.",
            "The authorization certification lane covers five source-bound workloads on the Python backend (payroll, orders, inventory, shipments, and a declared-API workload) with a Rust negative control; it does not change the 39-workload, 78-trial Campaign A scope.",
            "Consequence nodes, CAUSES_EFFECT bindings from services and APIs, and source-declared effect policies survive lowering. The candidate manifest carries the source revision hash, and conformance rejects a manifest from another revision. That preservation is not executable semantics and does not close W02.",
            "The only executable effect contract is a Python local record (positive amount, approved postcondition, one allow rule, SQLite commit with rollback). Rust refuses it, and every other effect kind or formula still fails closed.",
            "The lane's acceptance criteria are tracked in repository issue #158; the issue #161 corpus expansion is closed, and W02 stays IN_PROGRESS until every remaining gate passes.",
        ),
    ),
    WorkPackage(
        id="W03",
        title="Traceability and coverage",
        requirement=(
            "Make requirement to ISR element to test-oracle traceability first-class, "
            "with forward and reverse links and explicit orphan reporting."
        ),
        status=Status.IN_PROGRESS,
        dependencies=("W02",),
        evidence=(
            _code("reqgraph/core/graph.py"),
            _code("reqgraph/adapters/tor_isr.py"),
            _code("certification/campaign/runner.py"),
            _test("tests/cbc1/test_campaign_a.py"),
            _test("tests/test_source_bound_behavioral_projection.py"),
            _workflow(".github/workflows/root-canonical-suite.yml"),
        ),
        closure_gate=(
            "Every mandatory requirement has an implementation target and at least "
            "one verification oracle; orphans are reported, not ignored."
        ),
        claimed_tiers=(CertificationTier.STRUCTURAL, CertificationTier.BEHAVIORAL),
        limitations=(
            "Requirement to test-oracle edges are not first-class.",
            "Campaign A binds source-to-mapping-to-candidate hashes, but not a requirement-to-oracle traceability chain.",
        ),
    ),
    WorkPackage(
        id="W04",
        title="Architecture synthesis",
        requirement=(
            "Replace hardcoded architecture scores with measurable, reproducible "
            "decisions derived from requirements, constraints and backend capabilities."
        ),
        status=Status.IN_PROGRESS,
        dependencies=("W02",),
        evidence=(
            _code("vertical_slice/candidate_generation_d23.py"),
            _code("vertical_slice/architecture_selection_d24.py"),
            _test("tests/vs1/test_candidate_generation_d23.py"),
            _test("tests/vs1/test_architecture_selection_d24.py"),
            _workflow(".github/workflows/root-canonical-suite.yml"),
        ),
        closure_gate=(
            "Given identical inputs and toolchain, architecture candidates and scores "
            "are reproducible; unsupported options are excluded with reasons."
        ),
        claimed_tiers=(CertificationTier.STRUCTURAL,),
        limitations=(
            "Candidate scores remain analyst-assigned rather than derived from "
            "candidate content.",
        ),
    ),
    WorkPackage(
        id="W05",
        title="D15 architecture-to-implementation boundary",
        requirement=(
            "Consolidate the architecture selection and implementation boundary so a "
            "chosen architecture cannot silently alter ISR semantics or upstream "
            "authority."
        ),
        status=Status.IN_PROGRESS,
        dependencies=("W04",),
        evidence=(
            _code("vertical_slice/d25_authority_actuator.py"),
            _code("vertical_slice/regeneration.py"),
            _test("tests/vs1/test_d25_authority_actuator.py"),
            _test("tests/vs1/test_regeneration.py"),
            _test("tests/certification/test_architecture_mapping_producer.py"),
        ),
        closure_gate=(
            "Candidate architecture, compilation plan, artifacts and evidence all bind "
            "to the same ISR revision; incompatible mutation fails closed."
        ),
        claimed_tiers=(CertificationTier.STRUCTURAL, CertificationTier.BEHAVIORAL),
        limitations=(
            "D15 is lineage and provenance over hand-written files, not enforced code "
            "generation.",
        ),
    ),
    WorkPackage(
        id="W06",
        title="Technology-neutral compilation plan",
        requirement=(
            "Preserve typed fields, expressions, invariants, rules, API contracts, "
            "event schemas, effects and security policies throughout lowering, with "
            "schema/version compatibility and explicit unsupported-feature diagnostics."
        ),
        status=Status.IN_PROGRESS,
        dependencies=("W02",),
        evidence=(
            _code("compiler/core/plan.py"),
            _code("compiler/core/lowering.py"),
            _code("compiler/core/semantic_obligations.py"),
            _test("tests/test_adversarial_preservation.py"),
            _test("tests/cbc1/test_campaign_a.py"),
            _test("tests/test_source_bound_behavioral_projection.py"),
            _pr(137, "typed behavioural ISR contract and plan carriers merged"),
        ),
        closure_gate=(
            "Round-trip and contract tests prove no mandatory semantic element is lost "
            "between ISR and plan."
        ),
        claimed_tiers=(CertificationTier.STRUCTURAL, CertificationTier.BEHAVIORAL),
        limitations=(
            "Lowering checks effects, consequence bindings, and CAUSES_EFFECT edges against the source graph. Both real backends emit that set with the source revision hash, and conformance rejects an altered manifest.",
            "Adversarial checks cover a dropped effect, a missing or rewritten cause, an unresolved consequence, a missing service or API binding, a stale revision hash, and a same-hash payload from another candidate. Those checks do not prove execution and do not close W06.",
            "Preservation is not execution. Consequence semantics and general effect formulas are still refused, so the no-loss gate is not closed for every semantic category.",
        ),
    ),
    WorkPackage(
        id="W07",
        title="Backend compiler parity",
        requirement=(
            "Audit every advertised backend individually, keep real Python and Rust "
            "paths, and fail closed on semantic features a backend cannot implement."
        ),
        status=Status.IN_PROGRESS,
        dependencies=("W06",),
        evidence=(
            _code("compiler/backends/python_fastapi.py"),
            _code("compiler/backends/rust_axum.py"),
            _code("tiannara/application/compilation/backend_capability_registry.py"),
            _test("tests/test_no_passing_stubs.py"),
            _code("compiler/core/isr_parity.py"),
            _test("tests/integration/test_isr_api_parity.py"),
            _test("tests/integration/test_toolchain_parity.py"),
            _test("tests/cbc1/test_campaign_a.py"),
            _workflow(".github/workflows/cbc1-campaign-a.yml"),
            _artifact("cbc1-a-evidence", "78/78 CERTIFIED at d8f2a88e, real Docker"),
        ),
        closure_gate=(
            "Every advertised backend has a capability matrix, real builds, runtime "
            "tests, error-path tests and semantic conformance tests."
        ),
        claimed_tiers=(
            CertificationTier.STRUCTURAL,
            CertificationTier.BUILD,
            CertificationTier.RUNTIME,
            CertificationTier.BEHAVIORAL,
        ),
        limitations=(
            "Compiler capability gates are enforced in both real backends; remaining gaps are backend parity (Rust omits API contracts, authorization, typed events, invariants, and frontend carriers) and effect semantics, which neither backend supports.",
            "Node/Express targets are not exercised by Campaign A.",
            "Ruby and ASP.NET Core execute a fixed in-memory /api/records smoke test. Rails is still not booted. That smoke is not the ISR-derived API contract.",
            "tests/integration/test_isr_api_parity.py runs one declared ISR contract through Python, Elixir, and Rust. Each emits the declared routes plus GET /health and enforces validation, projection, authorization, authorized delete, and unchanged state after a denial. Ruby and C# still refuse api_contracts. Durable storage, bank_transfer, and shapes outside the slice stay refused.",
        ),
    ),
    WorkPackage(
        id="W08",
        title="Database and persistence generation",
        requirement=(
            "Generate complete migrations, constraints, indexes, foreign keys and "
            "reproducible initialization, and execute generated DDL against a real "
            "database."
        ),
        status=Status.IN_PROGRESS,
        dependencies=("W07",),
        evidence=(
            _code("compiler/backends/production/postgres_backend.py"),
            _code("constitutional_architecture/compilers/database/postgres/compiler.py"),
            _workflow(".github/workflows/root-canonical-suite.yml"),
        ),
        closure_gate=(
            "Fresh install, upgrade, downgrade and integrity tests run against the "
            "generated schema on a real database."
        ),
        claimed_tiers=(CertificationTier.BUILD, CertificationTier.OPERATIONAL),
        limitations=(
            "postgres.schema now emits upgrade and downgrade SQL. tests/integration/test_postgres_schema_runtime.py applies both to a temporary PostgreSQL cluster and checks unique and foreign-key failures. The test skips when server binaries are absent, so it is not yet a universal CI gate.",
            "Generated FastAPI and Rust applications still use in-memory repositories. The constitutional Alembic downgrade remains a no-op, and there is still no multi-revision migration chain.",
        ),
    ),
    WorkPackage(
        id="W09",
        title="API contract generation",
        requirement=(
            "Emit routes, schemas, validation, error models, versioning, pagination "
            "and idempotency as ISR-driven concepts, validating OpenAPI from the "
            "running service."
        ),
        status=Status.IN_PROGRESS,
        dependencies=("W07",),
        evidence=(
            _code("compiler/backends/python_fastapi.py"),
            _code("certification/stages/docker_stages.py"),
            _test("tests/test_no_passing_stubs.py"),
            _test("tests/integration/test_generated_effect_execution.py"),
            _workflow(".github/workflows/cbc1-campaign-a.yml"),
        ),
        closure_gate=(
            "Contract tests probe the live API against the approved specification, "
            "including malformed, missing, unauthorized and conflict cases."
        ),
        claimed_tiers=(
            CertificationTier.BUILD,
            CertificationTier.RUNTIME,
            CertificationTier.BEHAVIORAL,
        ),
        limitations=(
            "The Python record-effect route requires Idempotency-Key and is exercised through the generated ASGI app, including a missing key, a denied role, a malformed body, and a postcondition conflict. Removing the retry guard fails that suite.",
            "Versioning and pagination are still not ISR-driven API concepts. The idempotency header is limited to the supported record-effect route, and Rust does not expose it.",
        ),
    ),
    WorkPackage(
        id="W10",
        title="Event and asynchronous processing generation",
        requirement=(
            "Generate event schemas, producers, consumers, retries, dead-letter "
            "handling, delivery semantics and recovery from declared ISR behaviour."
        ),
        status=Status.IN_PROGRESS,
        dependencies=("W07",),
        evidence=(
            _code("compiler/backends/python_fastapi.py"),
            _code("compiler/backends/rust_axum.py"),
            _test("tests/test_no_passing_stubs.py"),
            _test("tests/integration/test_generated_event_delivery.py"),
        ),
        closure_gate=(
            "End-to-end event tests prove payload conformance, retry behaviour, "
            "duplicate handling, consumer failure and recovery."
        ),
        claimed_tiers=(CertificationTier.BUILD, CertificationTier.RUNTIME),
        limitations=(
            "Python can retry a generated consumer up to a declared maximum and write one dead letter after exhaustion. The generated tests read that SQLite ledger, and shortening the retry loop fails the exhaustion test.",
            "Rust refuses event delivery. There is no broker, ordering guarantee, duplicate-delivery protocol, or recovery after a transient failure.",
        ),
    ),
    WorkPackage(
        id="W11",
        title="RBAC/ABAC enforcement",
        requirement=(
            "Connect policy definitions to generated routes, services, data access "
            "and effects, enforcing authorization at every protected operation."
        ),
        status=Status.IN_PROGRESS,
        dependencies=("W09",),
        evidence=(
            _code("tiannara/application/enterprise/authorization.py"),
            _code("compiler/core/authorization.py"),
            _code("compiler/backends/python_fastapi.py"),
            _test("tests/test_authorization_policy_engine.py"),
            _test("tests/test_authorization_enforcement.py"),
            _test("tests/authorization/test_authorization_campaign.py"),
            _workflow(".github/workflows/authorization-campaign.yml"),
            _pr(125, "merged deny-by-default RBAC/ABAC policy engine"),
            _pr(165, "generated route authorization and operation-bound enforcement merged"),
        ),
        closure_gate=(
            "Independent tests prove allow and deny for every protected operation, "
            "including tenant isolation and escalation attempts."
        ),
        claimed_tiers=(CertificationTier.SECURITY,),
        limitations=(
            "Generated Python routes enforce signed-principal RBAC/ABAC for service- and API-operation-scoped policies, and the authorization lane certifies five source-bound workloads; Rust refuses authorization obligations and other advertised backends remain unproven.",
            "W11 remains open because closure requires every protected operation, tenant-isolation case, and escalation attempt to be independently exercised across all supported backends, not only the Python authorization lane.",
        ),
    ),
    WorkPackage(
        id="W12",
        title="Effects, idempotency and transaction coherence",
        requirement=(
            "Define side-effect contracts, idempotency keys, replay behaviour, "
            "transaction boundaries and compensation for supported workflows."
        ),
        status=Status.IN_PROGRESS,
        dependencies=("W09", "W10"),
        evidence=(
            _code("autonomous-api/app/engine/full_stack_verification.py"),
            _code("autonomous-api/app/engine/effect_consequences.py"),
            _code("isr/core/behavior.py"),
            _code("compiler/core/effect_contract.py"),
            _code("compiler/core/effects.py"),
            _code("compiler/backends/python_fastapi.py"),
            _code("certification/campaign/runner.py"),
            _test("tests/test_behavioral_capability_gate.py"),
            _test("tests/integration/test_generated_effect_execution.py"),
            _test("tests/cbc1/test_candidate_bound_full_stack_gate.py"),
            _test("tests/cbc1/test_source_bound_full_stack_projection.py"),
        ),
        closure_gate=(
            "Repeated and concurrent requests cannot produce duplicate prohibited "
            "effects; failures between persistence and publication are recoverable."
        ),
        claimed_tiers=(CertificationTier.BEHAVIORAL, CertificationTier.OPERATIONAL),
        limitations=(
            "Python executes one local record contract: one SQLite commit per idempotency key, replay of the same amount and approval, conflict rejection when that key is reused with a different payload, a separate commit for a different key, precondition rejection, authorization denial, and postcondition rollback. Generated pytest reads the ledger. Removing rollback or the conflict check fails the suite.",
            "That contract is not general effect semantics. Other formulas, external side effects, compensation, outbox publication, and cross-process recovery stay unsupported. Rust refuses the record contract and every typed effect.",
            "Campaign effect nodes remain declaration-level. Both backends still fail closed on EFFECT_SEMANTICS.",
        ),
    ),
    WorkPackage(
        id="W13",
        title="Frontend compiler completion",
        requirement=(
            "Complete real React output and audit other advertised frontend targets; "
            "generate routes, forms, validation, API clients, auth behaviour and "
            "loading/error states."
        ),
        status=Status.IN_PROGRESS,
        dependencies=("W09",),
        evidence=(
            _code("tiannara/application/compiler/react_frontend.py"),
            _code("tiannara/application/compiler/frontend_targets.py"),
            _code("constitutional_architecture/compilers/frontend/react/compiler.py"),
            _test("tests/test_frontend_targets.py"),
            _test("tests/test_react_compiler.py"),
            _pr(139, "buildable React frontend merged; browser-level evidence still missing"),
        ),
        closure_gate=(
            "Generated frontend packages install, compile, run and pass browser-level "
            "tests; placeholders cannot pass."
        ),
        claimed_tiers=(CertificationTier.BUILD, CertificationTier.BEHAVIORAL),
        limitations=(
            "CI runs npm install, Vitest, and a production build for the generated frontend, but no real-browser test exists.",
            "Registered frontend targets explicitly declare themselves not "
            "production-ready.",
            "PR #139 is merged; its frontend fixture uses a mocked API and does not prove live generated UI-to-API-to-persistence integration.",
            "React/Vite, the nine Tiannara frontend targets, and the constitutional React compiler are separate paths in COMPILER_TARGETS. None is a production compiler, and no browser journey against a live generated API has been run.",
        ),
    ),
    WorkPackage(
        id="W14",
        title="Full-stack integration",
        requirement=(
            "Connect generated UI, APIs, authentication, database, events and "
            "background work, and validate contract compatibility end to end."
        ),
        status=Status.IN_PROGRESS,
        dependencies=("W07", "W13"),
        evidence=(
            _code("autonomous-api/app/engine/source_bound_full_stack.py"),
            _test("tests/cbc1/test_source_bound_full_stack_projection.py"),
            _pr(140, "union integration merged; end-to-end generated journey still missing"),
        ),
        closure_gate=(
            "A clean-environment build and deployment exercise real user journeys "
            "from UI through persistence and back, including failures and denials."
        ),
        claimed_tiers=(CertificationTier.BEHAVIORAL, CertificationTier.OPERATIONAL),
        limitations=(
            "No generated UI-to-API-to-persistence end-to-end journey exists.",
            "PR #140 is merged, but its union integration does not establish a generated UI-to-API-to-persistence journey.",
        ),
    ),
    WorkPackage(
        id="W15",
        title="Behavioural test generation",
        requirement=(
            "Replace vacuous assertions with requirement-derived positive, negative, "
            "boundary, state-machine and cross-layer tests."
        ),
        status=Status.IN_PROGRESS,
        dependencies=("W03", "W07"),
        evidence=(
            _code("compiler/backends/python_fastapi.py"),
            _test("tests/test_no_passing_stubs.py"),
            _test("tests/test_test_compiler_no_vacuous_layers.py"),
            _test("tests/cbc1/test_campaign_a.py"),
        ),
        closure_gate=(
            "Tests fail when a requirement is deliberately broken; oracles are "
            "independent of generator assumptions."
        ),
        claimed_tiers=(CertificationTier.BEHAVIORAL,),
        limitations=(
            "Consumer-contract and chaos layers are declared unsupported and not "
            "emitted; no pact provider runtime or generated circuit-breaker "
            "instrumentation exists.",
            "Requirement-derived negative and boundary generation is not implemented.",
        ),
    ),
    WorkPackage(
        id="W16",
        title="Certification and verification hardening",
        requirement=(
            "Remove fail-open exceptions, simulated success, stale evidence reuse and "
            "ambiguous PASS states from certification paths."
        ),
        status=Status.IMPLEMENTED_UNVERIFIED,
        dependencies=("W03",),
        evidence=(
            _code("certification/stages/independent_verify.py"),
            _code("certification/stages/docker_stages.py"),
            _code("certification/campaign/runner.py"),
            _test("tests/test_no_passing_stubs.py"),
            _test("tests/test_passes/test_verification.py"),
            _test("tests/test_execution_evidence_truthfulness.py"),
            _test("tests/test_deployment_targets_fail_closed.py"),
            _test("tests/test_dast_fail_closed.py"),
            _test("tests/test_minimal_backend_smoke_fail_closed.py"),
            _workflow(".github/workflows/cbc1-campaign-a.yml"),
            _artifact("cbc1-a-evidence", "78/78 CERTIFIED at d8f2a88e, chain valid"),
        ),
        closure_gate=(
            "Fault injection proves missing evidence, verifier exceptions, skipped "
            "stages, stale hashes and simulated results cannot earn certification."
        ),
        claimed_tiers=(
            CertificationTier.STRUCTURAL,
            CertificationTier.BUILD,
            CertificationTier.RUNTIME,
        ),
        limitations=(
            "The minimal backend remains calibration-only; its artifacts are not "
            "production evidence.",
        ),
    ),
    WorkPackage(
        id="W17",
        title="Security and dependency assurance",
        requirement=(
            "Integrate static analysis, secret scanning, dependency and licence "
            "review, and DAST against running targets with severity-based gates."
        ),
        status=Status.IN_PROGRESS,
        dependencies=("W09",),
        evidence=(
            _workflow(".github/workflows/codeql.yml"),
            _workflow(".github/workflows/secret-scan.yml"),
            _workflow(".github/workflows/dependency-review.yml"),
            _code("tiannara/application/security/dast_campaign.py"),
            _test("tests/test_security_privacy_audit_hardening.py"),
            _test("tests/test_dast_fail_closed.py"),
        ),
        closure_gate=(
            "Findings gate by severity; DAST runs against the actual application; "
            "exceptions are explicit, justified and time-bound."
        ),
        claimed_tiers=(CertificationTier.SECURITY,),
        limitations=(
            "No real DAST scanner adapter ships; the campaign fails closed until a "
            "client is injected against a running target.",
            "No SBOM or licence policy is enforced in canonical gates.",
        ),
    ),
    WorkPackage(
        id="W18",
        title="Build, CI/CD and deployment",
        requirement=(
            "Complete deployment emitters and remove fabricated deployment handoffs; "
            "make workflows, configuration, secrets, rollback and health real."
        ),
        status=Status.IN_PROGRESS,
        dependencies=("W07",),
        evidence=(
            _workflow(".github/workflows/root-canonical-suite.yml"),
            _workflow(".github/workflows/cbc1-campaign-a.yml"),
            _code("certification/stages/docker_stages.py"),
            _test("tests/test_docker_execution_environment.py"),
            _test("tests/test_deployment_handoff_truthfulness.py"),
            _test("tests/test_deployment_targets_fail_closed.py"),
        ),
        closure_gate=(
            "A clean runner builds the candidate, deploys to a real test environment, "
            "probes it, captures logs and tears it down."
        ),
        claimed_tiers=(CertificationTier.BUILD, CertificationTier.OPERATIONAL),
        limitations=(
            "No runtime executor is shipped for the deployment targets; they fail "
            "closed until a real cluster/container adapter is injected.",
            "Generated CI and deploy workflows are not executed.",
        ),
    ),
    WorkPackage(
        id="W19",
        title="Observability and operational diagnosis",
        requirement=(
            "Generate correlated logs, metrics, traces, probes, alerts and diagnostic "
            "context tied to the deployed candidate, feeding controlled remediation."
        ),
        status=Status.IN_PROGRESS,
        dependencies=("W18",),
        evidence=(
            _code("observatory/backend/main.py"),
            _code("dashboard/src/application/statusStore.ts"),
            _test("tests/observatory/test_api.py"),
            _test("tests/observatory/test_gateway.py"),
        ),
        closure_gate=(
            "Injected failures are detected, traced, diagnosed from evidence and "
            "reported without claiming an unverified repair."
        ),
        claimed_tiers=(CertificationTier.OPERATIONAL,),
        limitations=(
            "The observability stack is detached from generated applications.",
            "No anomaly-to-incident-to-remediation loop is implemented.",
        ),
    ),
    WorkPackage(
        id="W20",
        title="Performance and resilience",
        requirement=(
            "Replace placeholder load and chaos tests with measurable throughput, "
            "latency, saturation, recovery and fault-injection tests."
        ),
        status=Status.IN_PROGRESS,
        dependencies=("W18",),
        evidence=(
            _code("certification/core/metrics.py"),
            _test("tests/cbc1/test_cost_energy_axis.py"),
            _test("tests/cbc1/test_cost_energy_aggregate.py"),
            _workflow(".github/workflows/cbc1-campaign-a.yml"),
        ),
        closure_gate=(
            "Repeatable load and resilience reports show whether the candidate meets "
            "declared targets; failures block claims."
        ),
        claimed_tiers=(CertificationTier.OPERATIONAL,),
        limitations=(
            "Cost and energy measure the harness lifecycle, not application load.",
            "Generated load and chaos tests are placeholders.",
        ),
    ),
    WorkPackage(
        id="W21",
        title="Existing-repository, multi-service and evolution capabilities",
        requirement=(
            "Move beyond regex-only repository analysis, map dependencies and "
            "interfaces, and generate coherent multi-service changes through "
            "controlled evolution cycles."
        ),
        status=Status.IN_PROGRESS,
        dependencies=("W07",),
        evidence=(
            _code("autonomous-api/app/engine/repository_audit_gate.py"),
            _code("autonomous-api/app/engine/repository_code_scan.py"),
            _workflow(".github/workflows/root-canonical-suite.yml"),
            _test("tests/test_autonomous_api_suite_coverage.py"),
        ),
        closure_gate=(
            "Existing-code changes preserve unrelated behaviour and contracts and "
            "pass regression suites; multi-service failures are tested as a whole."
        ),
        claimed_tiers=(CertificationTier.BEHAVIORAL, CertificationTier.OPERATIONAL),
        limitations=(
            "Analysis is regex-only.",
        ),
    ),
    WorkPackage(
        id="W22",
        title="Unified capability certification and release readiness",
        requirement=(
            "Consolidate capability declarations, acceptance profiles, evidence "
            "collection, regression matrices, provenance and release decisions into "
            "one auditable dossier."
        ),
        status=Status.IN_PROGRESS,
        dependencies=("W16", "W17", "W18", "W19", "W20", "W21"),
        evidence=(
            _code("certification/governance/registry.py"),
            _code("certification/evidence/infra_storm.py"),
            _code("certification/remediation/register.py"),
            _test("tests/cbc1/test_governance_registry.py"),
            _test("tests/test_remediation_register.py"),
        ),
        closure_gate=(
            "A release dossier maps every claimed capability to automated evidence "
            "and distinguishes structural, behavioural, security, operational and "
            "release claims."
        ),
        claimed_tiers=(CertificationTier.RELEASE,),
        limitations=(
            "Certification tiers are not yet enforced as release profiles.",
            "Release-dossier generation is not implemented.",
        ),
    ),
)

DEFECTS: tuple[Defect, ...] = (
    Defect(
        id="D01",
        title="Verification-engine exceptions downgraded to warnings (fail-open)",
        location="constitutional_architecture/compiler/passes/verification_pass.py",
        status=DefectStatus.VERIFIED,
        severity="critical",
        regression_test="tests/test_passes/test_verification.py",
        note="Now emits COMP-VERIFY-001 as a fatal diagnostic.",
    ),
    Defect(
        id="D02",
        title="Dry-run compiler gateway was the default and fabricated artifact paths",
        location="product_factory/hardening/compilation.py",
        status=DefectStatus.VERIFIED,
        severity="critical",
        regression_test="tests/test_product_factory_hardening.py",
        note=(
            "Default is now UnconfiguredCompilerGateway; the canonical regression "
            "proves the default fails closed, dry-run artifacts stay empty, and "
            "gateway self-reports cannot satisfy required backends."
        ),
    ),
    Defect(
        id="D03",
        title="Deployment handoff hardcoded deployed=True and healthy",
        location="tiannara/application/publication/deployment_handoff.py",
        status=DefectStatus.VERIFIED,
        severity="critical",
        regression_test="tests/test_deployment_handoff_truthfulness.py",
    ),
    Defect(
        id="D04",
        title="Deployment targets returned synthetic success and health",
        location="constitutional_architecture/deployment/targets/kubernetes_target.py",
        status=DefectStatus.VERIFIED,
        severity="high",
        regression_test="tests/test_deployment_targets_fail_closed.py",
        note=(
            "Kubernetes, Docker and local targets now require an injected "
            "TargetExecutor; without one they fail and health is unknown. An "
            "executor reporting success without an endpoint is rejected."
        ),
    ),
    Defect(
        id="D05",
        title="Constitutional pytest compiler emits assert True chaos/contract tests",
        location="constitutional_architecture/compilers/testing/pytest/compiler.py",
        status=DefectStatus.VERIFIED,
        severity="high",
        regression_test="tests/test_test_compiler_no_vacuous_layers.py",
        note=(
            "The assert-True chaos suite and pact placeholder suite are no longer "
            "emitted; unsupported layers are declared with reasons and metadata "
            "advertises only the layers actually generated."
        ),
    ),
    Defect(
        id="D06",
        title="DAST campaign simulated attack outcomes through hashes",
        location="tiannara/application/security/dast_campaign.py",
        status=DefectStatus.VERIFIED,
        severity="high",
        regression_test="tests/test_dast_fail_closed.py",
        note=(
            "run_dast now requires an injected DASTClient, dispatches every attack "
            "to it, preserves the returned outcomes in the ledger, and fails closed "
            "when no scanner is configured."
        ),
    ),
    Defect(
        id="D07",
        title="Phase-31 minimal container backend writes assert-True smoke tests",
        location="tiannara/infrastructure/backends/minimal_container_backend.py",
        status=DefectStatus.VERIFIED,
        severity="medium",
        regression_test="tests/test_minimal_backend_smoke_fail_closed.py",
        note=(
            "The generated smoke test imports the materialized health function; "
            "it passes on the generated app and fails when the artifact is broken. "
            "The backend remains calibration-only."
        ),
    ),
    Defect(
        id="D08",
        title="Repository-engine tests live outside the canonical testpaths",
        location="autonomous-api/tests",
        status=DefectStatus.VERIFIED,
        severity="medium",
        regression_test="tests/test_autonomous_api_suite_coverage.py",
        note=(
            "The Root Canonical Suite workflow runs the repository-engine suite in "
            "a dedicated Postgres-backed job on every PR and main push; a canonical "
            "contract keeps that wiring from silently disappearing."
        ),
    ),
)


COMPILER_TARGETS: tuple[CompilerTarget, ...] = (
    CompilerTarget(
        "python-fastapi", "canonical-backend", CompilerDisposition.REFERENCE, CompilerGate.EXECUTION, "W12",
        "Reference runtime for the supported record effect. General effect execution is still refused.",
    ),
    CompilerTarget(
        "rust-axum", "canonical-backend", CompilerDisposition.FAIL_CLOSED, CompilerGate.PARITY, "W07",
        "Axum implementation of the declared payroll HTTP contract is in progress (routes, validation, projection, authorization, shared error statuses). Parity is not established; build prerequisites and host linker environment are under investigation. Not production-ready.",
    ),
    CompilerTarget(
        "react-vite", "canonical-frontend", CompilerDisposition.SHELL, CompilerGate.INTEGRATION, "W13",
        "Canonical React/Vite path. Distinct from the Tiannara targets and the constitutional React compiler.",
    ),
    CompilerTarget(
        "react_ts", "tiannara-frontend", CompilerDisposition.SHELL, CompilerGate.PARITY, "W13",
        "Tiannara React target. A title page and Vitest check are not a production compiler.",
    ),
    CompilerTarget(
        "vue_ts", "tiannara-frontend", CompilerDisposition.SHELL, CompilerGate.PARITY, "W13",
        "Advertised Vue target. Not a production compiler.",
    ),
    CompilerTarget(
        "angular_ts", "tiannara-frontend", CompilerDisposition.SHELL, CompilerGate.PARITY, "W13",
        "Advertised Angular target. Not a production compiler.",
    ),
    CompilerTarget(
        "next_ts", "tiannara-frontend", CompilerDisposition.SHELL, CompilerGate.PARITY, "W13",
        "Advertised Next target. Not a production compiler.",
    ),
    CompilerTarget(
        "nuxt_ts", "tiannara-frontend", CompilerDisposition.SHELL, CompilerGate.PARITY, "W13",
        "Advertised Nuxt target. Not a production compiler.",
    ),
    CompilerTarget(
        "svelte_ts", "tiannara-frontend", CompilerDisposition.SHELL, CompilerGate.PARITY, "W13",
        "Advertised Svelte target. Not a production compiler.",
    ),
    CompilerTarget(
        "phoenix_liveview", "tiannara-frontend", CompilerDisposition.SHELL, CompilerGate.PARITY, "W13",
        "Advertised Phoenix LiveView target. Not a production compiler.",
    ),
    CompilerTarget(
        "hologram", "tiannara-frontend", CompilerDisposition.SHELL, CompilerGate.PARITY, "W13",
        "Advertised Hologram target. Not a production compiler.",
    ),
    CompilerTarget(
        "scenic", "tiannara-frontend", CompilerDisposition.SHELL, CompilerGate.PARITY, "W13",
        "Advertised Scenic target. Not a production compiler.",
    ),
    CompilerTarget(
        "constitutional-react", "constitutional-frontend", CompilerDisposition.SHELL, CompilerGate.PARITY, "W13",
        "Constitutional React compiler. Fixing React/Vite or Tiannara React does not cover this path.",
    ),
    CompilerTarget(
        "node-express", "advertised-backend", CompilerDisposition.FAIL_CLOSED, CompilerGate.PARITY, "W07",
        "No Node/Express compiler is in Campaign A. The target is tracked so it cannot be implied by omission.",
    ),
    CompilerTarget(
        "postgres-schema", "production-stack", CompilerDisposition.INTEGRATION_UNPROVEN, CompilerGate.INTEGRATION, "W08",
        "Emits upgrade and downgrade SQL. Generated FastAPI and Rust applications do not use that schema yet.",
    ),
    CompilerTarget(
        "docker-deployment", "production-stack", CompilerDisposition.INTEGRATION_UNPROVEN, CompilerGate.INTEGRATION, "W18",
        "Deployment artifacts are emitted. Generated applications are not proven to deploy from them.",
    ),
    CompilerTarget(
        "github-actions", "production-stack", CompilerDisposition.INTEGRATION_UNPROVEN, CompilerGate.INTEGRATION, "W18",
        "CI manifests are emitted. Emission is not a proven release pipeline for a generated application.",
    ),
    CompilerTarget(
        "elixir-phoenix", "canonical-backend", CompilerDisposition.RUNTIME_PROVEN, CompilerGate.EXECUTION, "W07",
        "Executes the declared payroll HTTP contract over OTP :gen_tcp: routes, validation, projection, authorization, and the shared error statuses. Not production-ready. Phoenix is not booted, durable storage and bank_transfer are refused, and other declared shapes outside that slice are refused.",
    ),
    CompilerTarget(
        "elixir-liveview", "canonical-frontend", CompilerDisposition.RUNTIME_PROVEN, CompilerGate.INTEGRATION, "W13",
        "Runnable page renderer. ExUnit checks the title, path, and unknown-route rejection. Not a LiveView browser journey and not production-ready.",
    ),
    CompilerTarget(
        "ruby-rails", "advertised-backend", CompilerDisposition.RUNTIME_PROVEN, CompilerGate.PARITY, "W07",
        "Ruby 4.0 executed the store test and a stdlib HTTP smoke test for health, create, fetch, and a missing id. That smoke is not the ISR-derived API contract. The Rails process was not booted. Not production-ready.",
    ),
    CompilerTarget(
        "aspnet-core", "advertised-backend", CompilerDisposition.RUNTIME_PROVEN, CompilerGate.PARITY, "W07",
        "The .NET 10 SDK starts the generated ASP.NET Core host and checks health, create, fetch, and a missing id. That smoke is not the ISR-derived API contract. Authorization, effects, and database persistence are not implemented. Not production-ready.",
    ),
)


def _path_problem(kind: EvidenceKind, ref: str, repo_root: Path) -> str | None:
    if kind is EvidenceKind.CODE:
        path = repo_root / ref
        return None if path.is_file() else f"code evidence does not exist: {ref}"
    if kind is EvidenceKind.TEST:
        path = repo_root / ref
        if not path.is_file():
            return f"test evidence does not exist: {ref}"
        if not ref.startswith("tests/"):
            return f"test evidence is outside the canonical suite: {ref}"
        return None
    if kind is EvidenceKind.WORKFLOW:
        path = repo_root / ref
        if not path.is_file():
            return f"workflow evidence does not exist: {ref}"
        if not ref.startswith(".github/workflows/"):
            return f"workflow evidence is outside .github/workflows: {ref}"
        return None
    if kind is EvidenceKind.PR:
        if not ref.startswith("PR#") or not ref[3:].isdigit():
            return f"malformed PR reference: {ref}"
        number = int(ref[3:])
        if number not in KNOWN_PRS:
            return f"unknown PR reference: {ref}"
        return None
    if kind is EvidenceKind.EVIDENCE:
        if not ref.startswith("workflow-artifact:"):
            return f"evidence reference must be a workflow artifact: {ref}"
        return None
    return f"unknown evidence kind: {kind}"


def _has_kind(package: WorkPackage, kind: EvidenceKind) -> bool:
    return any(item.kind is kind for item in package.evidence)


def _validate_dependencies(by_id: dict[str, WorkPackage]) -> list[str]:
    problems: list[str] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(package_id: str, trail: tuple[str, ...]) -> None:
        if package_id in visited:
            return
        if package_id in visiting:
            problems.append(f"dependency cycle: {' -> '.join(trail + (package_id,))}")
            return
        visiting.add(package_id)
        for dependency in by_id[package_id].dependencies:
            if dependency not in by_id:
                problems.append(f"{package_id} depends on unknown package: {dependency}")
                continue
            visit(dependency, trail + (package_id,))
        visiting.discard(package_id)
        visited.add(package_id)

    for package_id in by_id:
        visit(package_id, ())
    return problems


def _validate_compiler_targets(
    targets: Sequence[CompilerTarget],
    package_ids: set[str],
) -> list[str]:
    problems: list[str] = []
    required = {
        "python-fastapi", "rust-axum", "react-vite", "react_ts", "vue_ts", "angular_ts",
        "next_ts", "nuxt_ts", "svelte_ts", "phoenix_liveview", "hologram", "scenic",
        "constitutional-react", "node-express", "postgres-schema", "docker-deployment",
        "github-actions", "elixir-phoenix", "elixir-liveview", "ruby-rails", "aspnet-core",
    }
    seen: set[str] = set()
    for target in targets:
        if target.target_id in seen:
            problems.append(f"duplicate compiler target: {target.target_id}")
        seen.add(target.target_id)
        if target.work_package not in package_ids:
            problems.append(f"{target.target_id}: unknown work package {target.work_package}")
        if target.production_ready:
            problems.append(
                f"{target.target_id}: production_ready is not claimable from compiler registration"
            )
        if not target.note.strip():
            problems.append(f"{target.target_id}: compiler target requires an explicit note")
    missing = sorted(required - seen)
    if missing:
        problems.append(f"compiler target catalog is missing: {', '.join(missing)}")
    return problems


def validate_register(
    packages: Sequence[WorkPackage],
    defects: Sequence[Defect],
    repo_root: Path = REPO_ROOT,
    compiler_targets: Sequence[CompilerTarget] = COMPILER_TARGETS,
) -> list[str]:
    problems: list[str] = []
    expected_ids = [f"W{index:02d}" for index in range(1, 23)]
    actual_ids = [package.id for package in packages]
    if actual_ids != expected_ids:
        problems.append(
            f"work package ids must be exactly W01..W22 in order; got {actual_ids}"
        )
    duplicates = {pid for pid in actual_ids if actual_ids.count(pid) > 1}
    for duplicate in sorted(duplicates):
        problems.append(f"duplicate work package id: {duplicate}")

    by_id = {package.id: package for package in packages}
    if len(by_id) != len(packages):
        problems.append("work package ids are not unique")

    for package in packages:
        if not package.requirement.strip():
            problems.append(f"{package.id}: empty requirement")
        if not package.closure_gate.strip():
            problems.append(f"{package.id}: empty closure gate")
        if not package.claimed_tiers:
            problems.append(f"{package.id}: no claimed certification tiers")
        for dependency in package.dependencies:
            if dependency == package.id:
                problems.append(f"{package.id}: depends on itself")
        for item in package.evidence:
            problem = _path_problem(item.kind, item.ref, repo_root)
            if problem:
                problems.append(f"{package.id}: {problem}")
        if package.status in (Status.IMPLEMENTED_UNVERIFIED, Status.VERIFIED, Status.REGRESSION):
            if not _has_kind(package, EvidenceKind.CODE):
                problems.append(f"{package.id}: {package.status.value} without code evidence")
        if package.status is Status.IMPLEMENTED_UNVERIFIED:
            if not _has_kind(package, EvidenceKind.TEST):
                problems.append(
                    f"{package.id}: IMPLEMENTED_UNVERIFIED requires canonical test evidence"
                )
        if package.status is Status.VERIFIED:
            if not _has_kind(package, EvidenceKind.TEST):
                problems.append(f"{package.id}: VERIFIED without canonical test evidence")
            if not (
                _has_kind(package, EvidenceKind.WORKFLOW)
                or _has_kind(package, EvidenceKind.EVIDENCE)
            ):
                problems.append(
                    f"{package.id}: VERIFIED without workflow or artifact evidence"
                )
            if not package.verified_tiers:
                problems.append(f"{package.id}: VERIFIED without verified tiers")
        if package.verified_tiers:
            if package.status is not Status.VERIFIED:
                problems.append(
                    f"{package.id}: verified tiers require VERIFIED status, got "
                    f"{package.status.value}"
                )
            for tier in package.verified_tiers:
                if tier not in package.claimed_tiers:
                    problems.append(
                        f"{package.id}: verified tier {tier.value} is not claimed"
                    )
        if package.status is Status.IN_PROGRESS and not package.limitations:
            problems.append(f"{package.id}: IN_PROGRESS requires explicit limitations")

    problems.extend(_validate_dependencies(by_id) if len(by_id) == len(packages) else [])
    problems.extend(_validate_compiler_targets(compiler_targets, set(by_id)))

    seen_defects: set[str] = set()
    for defect in defects:
        if defect.id in seen_defects:
            problems.append(f"duplicate defect id: {defect.id}")
        seen_defects.add(defect.id)
        if defect.severity not in {"critical", "high", "medium", "low"}:
            problems.append(f"{defect.id}: invalid severity {defect.severity}")
        location = defect.location.split(":", 1)[0]
        if not (repo_root / location).exists():
            problems.append(f"{defect.id}: defect location does not exist: {location}")
        if defect.regression_test is not None:
            problem = _path_problem(EvidenceKind.TEST, defect.regression_test, repo_root)
            if problem:
                problems.append(f"{defect.id}: {problem}")
        if defect.status is DefectStatus.VERIFIED and defect.regression_test is None:
            problems.append(
                f"{defect.id}: VERIFIED defect requires a canonical regression test"
            )

    return problems


def register_payload() -> dict:
    return {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "work_packages": [
            {
                "id": package.id,
                "title": package.title,
                "requirement": package.requirement,
                "status": package.status.value,
                "dependencies": list(package.dependencies),
                "claimed_tiers": [tier.value for tier in package.claimed_tiers],
                "verified_tiers": [tier.value for tier in package.verified_tiers],
                "evidence": [
                    {"kind": item.kind.value, "ref": item.ref, "note": item.note}
                    for item in package.evidence
                ],
                "closure_gate": package.closure_gate,
                "limitations": list(package.limitations),
            }
            for package in WORK_PACKAGES
        ],
        "defects": [
            {
                "id": defect.id,
                "title": defect.title,
                "location": defect.location,
                "status": defect.status.value,
                "severity": defect.severity,
                "regression_test": defect.regression_test,
                "note": defect.note,
            }
            for defect in DEFECTS
        ],
        "known_prs": {f"PR#{number}": state for number, state in KNOWN_PRS.items()},
        "compiler_targets": [
            {
                "target_id": target.target_id,
                "family": target.family,
                "disposition": target.disposition.value,
                "gate": target.gate.value,
                "work_package": target.work_package,
                "production_ready": target.production_ready,
                "note": target.note,
            }
            for target in COMPILER_TARGETS
        ],
    }


def main(argv: Iterable[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    problems = validate_register(WORK_PACKAGES, DEFECTS)
    if "--json" in args:
        print(json.dumps(register_payload(), indent=2))
    if problems:
        for problem in problems:
            print(f"REGISTER-INVALID: {problem}", file=sys.stderr)
        return 1
    if "--check" in args:
        print(
            f"REGISTER-OK: {len(WORK_PACKAGES)} work packages, "
            f"{len(DEFECTS)} defects, schema {SCHEMA_ID}@{SCHEMA_VERSION}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
