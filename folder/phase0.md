Yes. Below is a **complete Phase 0 reference runtime codebase** for Tiannara.

This is the **Constitutional Kernel / Phase 0 runtime**: it establishes ISR-first discipline, requirement graph handling, ISR audit, traceability, immutable evidence, candidate lineage guards, certification evidence, and a minimal CLI demonstration pipeline.

This is a **reference implementation only**. Python is used for bootstrap practicality, but the ISR and platform constitution remain technology-neutral. Python here is an implementation detail, not architectural truth.

---

# Tiannara Phase 0 Runtime — Repository Scaffold

Create the following files exactly.

```text
tiannara-phase0/
├── .gitignore
├── README.md
├── pyproject.toml
├── src/
│   └── tiannara/
│       ├── __init__.py
│       ├── audit.py
│       ├── canonical.py
│       ├── candidates.py
│       ├── certification.py
│       ├── cli.py
│       ├── errors.py
│       ├── evidence.py
│       ├── hashing.py
│       ├── ids.py
│       ├── isr.py
│       ├── models.py
│       ├── requirements.py
│       ├── store.py
│       └── traceability.py
└── tests/
    └── test_phase0.py
```

---

# 1. `pyproject.toml`

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "tiannara-phase0"
version = "0.0.1"
description = "Tiannara Phase 0 constitutional kernel reference runtime"
requires-python = ">=3.11"

[project.scripts]
tiannara = "tiannara.cli:main"

[tool.setuptools.packages.find]
where = ["src"]
```

---

# 2. `.gitignore`

```gitignore
__pycache__/
*.pyc
*.pyo
*.egg-info/
.venv/
venv/
var/
dist/
build/
```

---

# 3. `README.md`

```markdown
# Tiannara Phase 0 — Constitutional Kernel Reference Runtime

This is the Phase 0 runtime for Tiannara.

Its purpose is to establish the constitutional foundation:

- ISR is the sole architectural source of truth.
- Requirements flow into a Requirement Graph.
- ISR must be audited before compilation.
- Traceability is mandatory.
- Evidence is immutable and hash-chained.
- Certification requires passing evidence.
- Evolution candidates must not be no-op or cosmetic.
- Generated implementation technologies are not allowed inside the ISR.

This is a reference runtime. It is not a certified production platform yet.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Run tests

```bash
python -m unittest discover -s tests -v
```

## Initialize a local Phase 0 workspace

```bash
tiannara --root ./var/tiannara init
```

## Run the Phase 0 demonstration pipeline

```bash
tiannara --root ./var/tiannara demo
```

## Verify the evidence ledger

```bash
tiannara --root ./var/tiannara verify-evidence
```

## Show an artifact

```bash
tiannara --root ./var/tiannara show-artifact isr ISR-DEMO-001
```
```

---

# 4. `src/tiannara/__init__.py`

```python
__version__ = "0.0.1"
```

---

# 5. `src/tiannara/errors.py`

```python
class TiannaraError(Exception):
    """Base exception for all Tiannara errors."""


class ValidationError(TiannaraError):
    """Raised when a contract, schema, or invariant is violated."""


class LeakageError(TiannaraError):
    """Raised when implementation technology leaks into the ISR."""


class TraceabilityError(TiannaraError):
    """Raised when traceability is missing or invalid."""


class NoOpEvolutionError(TiannaraError):
    """Raised when an evolution candidate is cosmetic or no-op."""


class EvidenceError(TiannaraError):
    """Raised when evidence is invalid, tampered with, or insufficient."""


class CertificationError(TiannaraError):
    """Raised when certification cannot be issued."""
```

---

# 6. `src/tiannara/canonical.py`

```python
from __future__ import annotations

import json
from typing import Any


def canonical_json(obj: Any) -> bytes:
    """
    Produce deterministic canonical JSON bytes.

    This is used for stable hashing of Tiannara artifacts.
    """
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
```

---

# 7. `src/tiannara/hashing.py`

```python
from __future__ import annotations

import hashlib
from typing import Any

from .canonical import canonical_json


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hash_obj(obj: Any) -> str:
    """
    Deterministically hash any JSON-serializable object.
    """
    return sha256_hex(canonical_json(obj))
```

---

# 8. `src/tiannara/ids.py`

```python
from __future__ import annotations

import uuid


def new_id(prefix: str) -> str:
    """
    Generate a human-readable unique identifier.

    Example:
        isr_9f2c4d1e8a7b6c5d4e3f
    """
    return f"{prefix}_{uuid.uuid4().hex[:20]}"
```

---

# 9. `src/tiannara/store.py`

```python
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from .hashing import hash_obj


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Store:
    """
    Filesystem-backed artifact store for Phase 0.

    This store is intentionally simple and auditable.
    It writes JSON artifacts and append-only JSONL ledgers.
    """

    def __init__(self, root: Path | str):
        self.root = Path(root)

    def ensure(self) -> None:
        for directory in [
            "artifacts",
            "evidence",
            "traceability",
            "certification",
        ]:
            (self.root / directory).mkdir(parents=True, exist_ok=True)

    def artifact_path(self, kind: str, artifact_id: str) -> Path:
        return self.root / "artifacts" / kind / f"{artifact_id}.json"

    def write_artifact(
        self,
        kind: str,
        artifact_id: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        content_hash = hash_obj(payload)
        envelope = {
            "kind": kind,
            "id": artifact_id,
            "content_hash": content_hash,
            "payload": payload,
            "stored_at": utcnow_iso(),
        }

        path = self.artifact_path(kind, artifact_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(envelope, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return envelope

    def read_artifact(self, kind: str, artifact_id: str) -> Dict[str, Any]:
        path = self.artifact_path(kind, artifact_id)
        if not path.exists():
            raise FileNotFoundError(f"artifact not found: {kind}/{artifact_id}")

        return json.loads(path.read_text(encoding="utf-8"))

    def list_artifact_ids(self, kind: str) -> List[str]:
        directory = self.root / "artifacts" / kind
        if not directory.exists():
            return []

        return sorted(path.stem for path in directory.glob("*.json"))

    def append_jsonl(self, relative_path: str, obj: Dict[str, Any]) -> None:
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(obj, sort_keys=True, separators=(",", ":")))
            handle.write("\n")

    def read_jsonl(self, relative_path: str) -> List[Dict[str, Any]]:
        path = self.root / relative_path
        if not path.exists():
            return []

        items: List[Dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    items.append(json.loads(line))

        return items
```

---

# 10. `src/tiannara/models.py`

```python
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Requirement:
    requirement_id: str
    title: str
    source: str
    type: str
    priority: str
    epistemic_status: str
    dependencies: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    acceptance_criteria: List[str] = field(default_factory=list)
    verification_strategy: List[str] = field(default_factory=list)
    isr_mappings: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=utcnow_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RequirementGraph:
    graph_id: str
    version: str
    requirements: List[Requirement]
    edges: List[Dict[str, str]]
    created_by: str
    created_at: str = field(default_factory=utcnow_iso)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "graph_id": self.graph_id,
            "version": self.version,
            "requirements": [requirement.to_dict() for requirement in self.requirements],
            "edges": self.edges,
            "created_by": self.created_by,
            "created_at": self.created_at,
        }


@dataclass
class ISRManifest:
    isr_id: str
    version: str
    requirement_graph_hash: str
    domains: List[str]
    capabilities: List[str]
    entities: List[Dict[str, Any]]
    aggregates: List[str]
    workflows: List[str]
    commands: List[str]
    queries: List[str]
    events: List[str]
    interfaces: List[Dict[str, Any]]
    security_policies: List[str]
    performance_constraints: List[str]
    deployment_constraints: List[str]
    observability_requirements: List[str]
    assumptions: List[str]
    unresolved_questions: List[str]
    metadata: Dict[str, Any]
    created_by: str
    created_at: str = field(default_factory=utcnow_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ISRAudit:
    audit_id: str
    isr_id: str
    isr_hash: str
    requirement_graph_hash: str
    status: str
    completeness_score: float
    traceability_score: float
    leakage_report: Dict[str, Any]
    invariant_report: Dict[str, Any]
    ambiguity_report: Dict[str, Any]
    architectural_risks: List[str]
    unresolved_questions: List[str]
    auditor_identity: str
    created_at: str = field(default_factory=utcnow_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TraceabilityLink:
    link_id: str
    source_id: str
    target_id: str
    relation_type: str
    evidence_ids: List[str]
    confidence: float
    created_by: str
    status: str
    created_at: str = field(default_factory=utcnow_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BackendContract:
    backend_id: str
    backend_version: str
    backend_type: str
    supported_isr_capabilities: List[str]
    supported_workload_categories: List[str]
    target_platform: str
    dependencies: List[str]
    verification_capabilities: List[str]
    security_characteristics: List[str]
    deployment_targets: List[str]
    observability_capabilities: List[str]
    limitations: List[str]
    status: str
    created_by: str
    created_at: str = field(default_factory=utcnow_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Candidate:
    candidate_id: str
    parent_candidate_id: Optional[str]
    isr_id: str
    isr_hash: str
    genome_hash: str
    backend_id: str
    artifact_identity: str
    changed_dimensions: List[str]
    unchanged_dimensions: List[str]
    hypothesis: str
    expected_outcome: str
    measurement_strategy: str
    acceptance_criteria: str
    falsifier: str
    novelty_proof: str
    status: str
    created_at: str = field(default_factory=utcnow_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Evidence:
    evidence_id: str
    trial_id: str
    stage: str
    subject_type: str
    subject_id: str
    artifact_hashes: Dict[str, str]
    result: str
    environment: Dict[str, Any]
    compiler_versions: Dict[str, str]
    backend_versions: Dict[str, str]
    configuration: Dict[str, Any]
    seed: Optional[str]
    created_at: str = field(default_factory=utcnow_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CertificationDecision:
    certification_id: str
    subject_type: str
    subject_id: str
    isr_id: str
    candidate_id: str
    backend_id: str
    artifact_id: str
    audit_id: str
    evidence_ids: List[str]
    decision: str
    rationale: str
    confidence: float
    policy_id: str
    decision_authority: str
    created_at: str = field(default_factory=utcnow_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
```

---

# 11. `src/tiannara/requirements.py`

```python
from __future__ import annotations

from typing import Dict, List

from .errors import ValidationError
from .models import Requirement, RequirementGraph

ALLOWED_EPISTEMIC_STATUSES = {
    "KNOWN",
    "UNKNOWN",
    "ASSUMED",
    "INFERRED",
    "REQUIRED_DECISION",
}

ALLOWED_PRIORITIES = {
    "MUST",
    "SHOULD",
    "COULD",
    "WONT",
}

ALLOWED_EDGE_RELATIONS = {
    "DEPENDS_ON",
    "REFINES",
    "CONFLICTS_WITH",
    "RELATED_TO",
}


def validate_requirement(requirement: Requirement) -> None:
    required_fields = [
        "requirement_id",
        "title",
        "source",
        "type",
        "priority",
        "epistemic_status",
    ]

    for field_name in required_fields:
        value = getattr(requirement, field_name, None)
        if not value:
            raise ValidationError(f"requirement.{field_name} is required")

    if requirement.epistemic_status not in ALLOWED_EPISTEMIC_STATUSES:
        raise ValidationError(
            f"requirement.epistemic_status must be one of {sorted(ALLOWED_EPISTEMIC_STATUSES)}"
        )

    if requirement.priority not in ALLOWED_PRIORITIES:
        raise ValidationError(
            f"requirement.priority must be one of {sorted(ALLOWED_PRIORITIES)}"
        )


def build_graph(
    graph_id: str,
    version: str,
    requirements: List[Requirement],
    edges: List[Dict[str, str]],
    created_by: str,
) -> RequirementGraph:
    if not graph_id:
        raise ValidationError("graph_id is required")

    if not version:
        raise ValidationError("version is required")

    if not created_by:
        raise ValidationError("created_by is required")

    requirement_ids = set()

    for requirement in requirements:
        validate_requirement(requirement)

        if requirement.requirement_id in requirement_ids:
            raise ValidationError(
                f"duplicate requirement_id: {requirement.requirement_id}"
            )

        requirement_ids.add(requirement.requirement_id)

    for requirement in requirements:
        for dependency in requirement.dependencies:
            if dependency not in requirement_ids:
                raise ValidationError(
                    f"requirement {requirement.requirement_id} depends on unknown requirement {dependency}"
                )

    for edge in edges:
        for key in ["source", "target", "relation"]:
            if key not in edge:
                raise ValidationError(f"edge missing required key: {key}")

        if edge["source"] not in requirement_ids:
            raise ValidationError(f"edge source not found: {edge['source']}")

        if edge["target"] not in requirement_ids:
            raise ValidationError(f"edge target not found: {edge['target']}")

        if edge["relation"] not in ALLOWED_EDGE_RELATIONS:
            raise ValidationError(
                f"edge relation must be one of {sorted(ALLOWED_EDGE_RELATIONS)}"
            )

    return RequirementGraph(
        graph_id=graph_id,
        version=version,
        requirements=requirements,
        edges=edges,
        created_by=created_by,
    )
```

---

# 12. `src/tiannara/isr.py`

```python
from __future__ import annotations

import re
from typing import Any, Dict, List

from .canonical import canonical_json

LEAKAGE_TERMS = [
    "postgres",
    "postgresql",
    "mysql",
    "sqlite",
    "mongodb",
    "redis",
    "kafka",
    "rabbitmq",
    "nats",
    "sqs",
    "fastapi",
    "spring boot",
    "springboot",
    "django",
    "laravel",
    "react",
    "vue",
    "angular",
    "flutter",
    "rust",
    "python",
    "golang",
    "java",
    "csharp",
    "elixir",
    "typescript",
    "aws",
    "azure",
    "gcp",
    "kubernetes",
    "docker",
    "terraform",
    "pulumi",
]

LEAKAGE_REGEX = re.compile(
    r"\b(?:" + "|".join(re.escape(term) for term in LEAKAGE_TERMS) + r")\b",
    re.IGNORECASE,
)

REQUIRED_ISR_KEYS = {
    "isr_id",
    "version",
    "requirement_graph_hash",
    "domains",
    "capabilities",
    "entities",
    "aggregates",
    "workflows",
    "commands",
    "queries",
    "events",
    "interfaces",
    "security_policies",
    "performance_constraints",
    "deployment_constraints",
    "observability_requirements",
    "assumptions",
    "unresolved_questions",
    "metadata",
    "created_by",
    "created_at",
}

LIST_ISR_KEYS = {
    "domains",
    "capabilities",
    "entities",
    "aggregates",
    "workflows",
    "commands",
    "queries",
    "events",
    "interfaces",
    "security_policies",
    "performance_constraints",
    "deployment_constraints",
    "observability_requirements",
    "assumptions",
    "unresolved_questions",
}

STRING_ISR_KEYS = {
    "isr_id",
    "version",
    "requirement_graph_hash",
    "created_by",
    "created_at",
}


def validate_isr_payload(payload: Dict[str, Any]) -> List[str]:
    issues: List[str] = []

    for key in REQUIRED_ISR_KEYS:
        if key not in payload:
            issues.append(f"missing:{key}")

    for key in LIST_ISR_KEYS:
        if key in payload and not isinstance(payload[key], list):
            issues.append(f"not_list:{key}")

    for key in STRING_ISR_KEYS:
        if key in payload and not isinstance(payload[key], str):
            issues.append(f"not_string:{key}")

    if "metadata" in payload and not isinstance(payload["metadata"], dict):
        issues.append("not_dict:metadata")

    return issues


def detect_leakage(payload: Dict[str, Any]) -> List[str]:
    """
    Detect implementation technology leakage inside the ISR.

    The ISR must remain technology-neutral.
    Terms such as postgres, redis, kafka, react, docker, kubernetes,
    and language/framework names are not allowed in Phase 0 ISR content.
    """
    text = canonical_json(payload).decode("utf-8")
    matches = LEAKAGE_REGEX.finditer(text)
    return sorted(set(match.group(0).lower() for match in matches))


def compute_completeness(payload: Dict[str, Any]) -> float:
    score = 0.0

    if payload.get("domains"):
        score += 0.10

    if payload.get("capabilities"):
        score += 0.20

    if payload.get("entities"):
        score += 0.20

    if payload.get("workflows"):
        score += 0.10

    if payload.get("interfaces"):
        score += 0.10

    if payload.get("security_policies"):
        score += 0.10

    if payload.get("performance_constraints"):
        score += 0.05

    if payload.get("deployment_constraints"):
        score += 0.05

    if payload.get("observability_requirements"):
        score += 0.05

    if not payload.get("unresolved_questions"):
        score += 0.05

    return round(min(1.0, score), 4)
```

---

# 13. `src/tiannara/traceability.py`

```python
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .errors import ValidationError
from .ids import new_id
from .models import TraceabilityLink
from .store import Store

ALLOWED_RELATION_TYPES = {
    "REQUIREMENT_TO_ISR",
    "ISR_TO_ARCHITECTURE_DECISION",
    "ARCHITECTURE_DECISION_TO_CANDIDATE",
    "CANDIDATE_TO_BACKEND",
    "BACKEND_TO_ARTIFACT",
    "ARTIFACT_TO_TEST",
    "TEST_TO_EVIDENCE",
    "EVIDENCE_TO_CERTIFICATION",
}


class TraceabilityStore:
    def __init__(self, store: Store):
        self.store = store
        self.relative_path = "traceability/links.jsonl"

    def add_link(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
        created_by: str,
        evidence_ids: Optional[List[str]] = None,
        confidence: float = 1.0,
        status: str = "ACTIVE",
    ) -> TraceabilityLink:
        if not source_id:
            raise ValidationError("source_id is required")

        if not target_id:
            raise ValidationError("target_id is required")

        if relation_type not in ALLOWED_RELATION_TYPES:
            raise ValidationError(
                f"relation_type must be one of {sorted(ALLOWED_RELATION_TYPES)}"
            )

        if not created_by:
            raise ValidationError("created_by is required")

        link = TraceabilityLink(
            link_id=new_id("link"),
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            evidence_ids=evidence_ids or [],
            confidence=confidence,
            created_by=created_by,
            status=status,
        )

        self.store.append_jsonl(self.relative_path, link.to_dict())
        return link

    def links(self) -> List[Dict[str, Any]]:
        return self.store.read_jsonl(self.relative_path)

    def has_link(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
    ) -> bool:
        return any(
            link.get("source_id") == source_id
            and link.get("target_id") == target_id
            and link.get("relation_type") == relation_type
            for link in self.links()
        )

    def links_for_source(self, source_id: str) -> List[Dict[str, Any]]:
        return [link for link in self.links() if link.get("source_id") == source_id]

    def links_for_target(self, target_id: str) -> List[Dict[str, Any]]:
        return [link for link in self.links() if link.get("target_id") == target_id]
```

---

# 14. `src/tiannara/audit.py`

```python
from __future__ import annotations

from typing import Any, Dict

from .ids import new_id
from .isr import compute_completeness, detect_leakage, validate_isr_payload
from .models import ISRAudit


def audit_isr(
    *,
    isr_envelope: Dict[str, Any],
    graph_envelope: Dict[str, Any],
    trace_store: Any,
    auditor_identity: str,
) -> ISRAudit:
    payload = isr_envelope["payload"]
    issues = validate_isr_payload(payload)

    if payload.get("requirement_graph_hash") != graph_envelope["content_hash"]:
        issues.append("requirement_graph_hash_mismatch")

    leakage_terms = detect_leakage(payload)
    if leakage_terms:
        issues.append("implementation_leakage")

    requirements = graph_envelope["payload"].get("requirements", [])
    missing_traceability = []

    for requirement in requirements:
        requirement_id = requirement.get("requirement_id")
        if not trace_store.has_link(
            source_id=requirement_id,
            target_id=payload.get("isr_id"),
            relation_type="REQUIREMENT_TO_ISR",
        ):
            missing_traceability.append(requirement_id)

    if missing_traceability:
        issues.append("missing_traceability")

    total_requirements = len(requirements)
    if total_requirements == 0:
        issues.append("no_requirements")
        traceability_score = 0.0
    else:
        traceability_score = round(
            (total_requirements - len(missing_traceability)) / total_requirements,
            4,
        )

    completeness_score = compute_completeness(payload)
    unresolved_questions = payload.get("unresolved_questions", [])

    if unresolved_questions:
        issues.append("unresolved_questions_present")

    status = "AUDITED"
    if issues or completeness_score < 0.7:
        status = "REJECTED"

    return ISRAudit(
        audit_id=new_id("audit"),
        isr_id=payload.get("isr_id", ""),
        isr_hash=isr_envelope["content_hash"],
        requirement_graph_hash=payload.get("requirement_graph_hash", ""),
        status=status,
        completeness_score=completeness_score,
        traceability_score=traceability_score,
        leakage_report={
            "clean": not leakage_terms,
            "leaked_terms": leakage_terms,
        },
        invariant_report={
            "issues": issues,
            "missing_traceability": missing_traceability,
        },
        ambiguity_report={
            "unresolved_questions": unresolved_questions,
            "assumptions": payload.get("assumptions", []),
        },
        architectural_risks=payload.get("metadata", {}).get("architectural_risks", []),
        unresolved_questions=unresolved_questions,
        auditor_identity=auditor_identity,
    )
```

---

# 15. `src/tiannara/candidates.py`

```python
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .errors import NoOpEvolutionError, ValidationError
from .ids import new_id
from .models import BackendContract, Candidate
from .store import Store


def register_backend(store: Store, backend: BackendContract) -> Dict[str, Any]:
    if not backend.backend_id:
        raise ValidationError("backend.backend_id is required")

    if not backend.backend_version:
        raise ValidationError("backend.backend_version is required")

    if not backend.backend_type:
        raise ValidationError("backend.backend_type is required")

    if backend.status != "ACTIVE":
        raise ValidationError("backend.status must be ACTIVE")

    return store.write_artifact(
        kind="backend_contract",
        artifact_id=backend.backend_id,
        payload=backend.to_dict(),
    )


def create_candidate(
    store: Store,
    *,
    isr_envelope: Dict[str, Any],
    backend_envelope: Dict[str, Any],
    genome_hash: str,
    artifact_identity: str,
    changed_dimensions: List[str],
    unchanged_dimensions: List[str],
    hypothesis: str,
    expected_outcome: str,
    measurement_strategy: str,
    acceptance_criteria: str,
    falsifier: str,
    novelty_proof: str,
    parent_candidate_id: Optional[str] = None,
) -> Dict[str, Any]:
    if not genome_hash:
        raise ValidationError("genome_hash is required")

    if not artifact_identity:
        raise ValidationError("artifact_identity is required")

    if not changed_dimensions:
        raise ValidationError("changed_dimensions must not be empty")

    if not hypothesis:
        raise ValidationError("hypothesis is required")

    if not expected_outcome:
        raise ValidationError("expected_outcome is required")

    if not measurement_strategy:
        raise ValidationError("measurement_strategy is required")

    if not acceptance_criteria:
        raise ValidationError("acceptance_criteria is required")

    if not falsifier:
        raise ValidationError("falsifier is required")

    if not novelty_proof:
        raise ValidationError("novelty_proof is required")

    backend_payload = backend_envelope["payload"]

    if backend_payload.get("status") != "ACTIVE":
        raise ValidationError("backend must be ACTIVE")

    if parent_candidate_id:
        parent_envelope = store.read_artifact("candidate", parent_candidate_id)
        parent_payload = parent_envelope["payload"]

        if artifact_identity == parent_payload.get("artifact_identity"):
            raise NoOpEvolutionError(
                "candidate artifact_identity is unchanged from parent; "
                "this is a NO_OP_EVOLUTION"
            )

        if (
            backend_envelope["id"] == parent_payload.get("backend_id")
            and genome_hash == parent_payload.get("genome_hash")
        ):
            raise NoOpEvolutionError(
                "candidate backend and genome are unchanged from parent; "
                "this is a NO_OP_EVOLUTION"
            )

    candidate = Candidate(
        candidate_id=new_id("candidate"),
        parent_candidate_id=parent_candidate_id,
        isr_id=isr_envelope["payload"]["isr_id"],
        isr_hash=isr_envelope["content_hash"],
        genome_hash=genome_hash,
        backend_id=backend_envelope["id"],
        artifact_identity=artifact_identity,
        changed_dimensions=changed_dimensions,
        unchanged_dimensions=unchanged_dimensions,
        hypothesis=hypothesis,
        expected_outcome=expected_outcome,
        measurement_strategy=measurement_strategy,
        acceptance_criteria=acceptance_criteria,
        falsifier=falsifier,
        novelty_proof=novelty_proof,
        status="PROPOSED",
    )

    return store.write_artifact(
        kind="candidate",
        artifact_id=candidate.candidate_id,
        payload=candidate.to_dict(),
    )
```

---

# 16. `src/tiannara/evidence.py`

```python
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .errors import EvidenceError
from .hashing import hash_obj
from .ids import new_id
from .models import Evidence
from .store import Store

ALLOWED_EVIDENCE_RESULTS = {
    "PASS",
    "FAIL",
    "PARTIAL",
    "ERROR",
}


class EvidenceLedger:
    """
    Append-only hash-chained evidence ledger.

    Evidence is immutable.
    A retry is a new evidence entry.
    A failed trial remains failed.
    """

    def __init__(self, store: Store):
        self.store = store
        self.relative_path = "evidence/ledger.jsonl"

    def entries(self) -> List[Dict[str, Any]]:
        return self.store.read_jsonl(self.relative_path)

    def last_hash(self) -> str:
        entries = self.entries()
        if not entries:
            return "0" * 64

        return entries[-1]["entry_hash"]

    def append(
        self,
        *,
        trial_id: str,
        stage: str,
        subject_type: str,
        subject_id: str,
        result: str,
        artifact_hashes: Optional[Dict[str, str]] = None,
        environment: Optional[Dict[str, Any]] = None,
        compiler_versions: Optional[Dict[str, str]] = None,
        backend_versions: Optional[Dict[str, str]] = None,
        configuration: Optional[Dict[str, Any]] = None,
        seed: Optional[str] = None,
    ) -> Dict[str, Any]:
        if result not in ALLOWED_EVIDENCE_RESULTS:
            raise EvidenceError(
                f"evidence result must be one of {sorted(ALLOWED_EVIDENCE_RESULTS)}"
            )

        evidence = Evidence(
            evidence_id=new_id("evidence"),
            trial_id=trial_id,
            stage=stage,
            subject_type=subject_type,
            subject_id=subject_id,
            artifact_hashes=artifact_hashes or {},
            result=result,
            environment=environment or {},
            compiler_versions=compiler_versions or {},
            backend_versions=backend_versions or {},
            configuration=configuration or {},
            seed=seed,
        )

        entry = evidence.to_dict()
        entry["previous_hash"] = self.last_hash()
        entry_hash = hash_obj(entry)
        entry["entry_hash"] = entry_hash

        self.store.append_jsonl(self.relative_path, entry)
        return entry

    def get(self, evidence_id: str) -> Optional[Dict[str, Any]]:
        for entry in self.entries():
            if entry.get("evidence_id") == evidence_id:
                return entry

        return None

    def verify(self) -> bool:
        previous_hash = "0" * 64

        for entry in self.entries():
            stored_hash = entry.get("entry_hash")
            if not stored_hash:
                raise EvidenceError("evidence entry missing entry_hash")

            if entry.get("previous_hash") != previous_hash:
                raise EvidenceError("evidence hash chain is broken")

            entry_without_hash = {
                key: value for key, value in entry.items() if key != "entry_hash"
            }

            computed_hash = hash_obj(entry_without_hash)
            if computed_hash != stored_hash:
                raise EvidenceError("evidence entry hash mismatch")

            previous_hash = stored_hash

        return True
```

---

# 17. `src/tiannara/certification.py`

```python
from __future__ import annotations

from typing import Any, Dict, List

from .errors import CertificationError, ValidationError
from .evidence import EvidenceLedger
from .ids import new_id
from .models import CertificationDecision
from .store import Store

ALLOWED_CERTIFICATION_SUBJECTS = {
    "isr",
    "candidate",
    "artifact",
    "system",
}


def certify_candidate(
    store: Store,
    evidence_ledger: EvidenceLedger,
    *,
    subject_type: str,
    subject_id: str,
    isr_id: str,
    candidate_id: str,
    backend_id: str,
    artifact_id: str,
    audit_id: str,
    evidence_ids: List[str],
    decision_authority: str,
    policy_id: str = "phase0-certification-v1",
    rationale: str = "",
    confidence: float = 1.0,
) -> Dict[str, Any]:
    if subject_type not in ALLOWED_CERTIFICATION_SUBJECTS:
        raise ValidationError(
            f"subject_type must be one of {sorted(ALLOWED_CERTIFICATION_SUBJECTS)}"
        )

    if not evidence_ids:
        raise ValidationError("certification requires at least one evidence object")

    audit_envelope = store.read_artifact("isr_audit", audit_id)
    audit_payload = audit_envelope["payload"]

    if audit_payload.get("isr_id") != isr_id:
        raise CertificationError("audit does not belong to this ISR")

    if audit_payload.get("status") not in {"AUDITED", "VERIFIED", "CERTIFIED"}:
        raise CertificationError("ISR audit is not passing")

    evidence_ledger.verify()

    for evidence_id in evidence_ids:
        entry = evidence_ledger.get(evidence_id)

        if entry is None:
            raise CertificationError(f"evidence not found: {evidence_id}")

        if entry.get("result") != "PASS":
            raise CertificationError(
                f"evidence {evidence_id} is not PASS; certification denied"
            )

    decision = CertificationDecision(
        certification_id=new_id("cert"),
        subject_type=subject_type,
        subject_id=subject_id,
        isr_id=isr_id,
        candidate_id=candidate_id,
        backend_id=backend_id,
        artifact_id=artifact_id,
        audit_id=audit_id,
        evidence_ids=evidence_ids,
        decision="CERTIFIED",
        rationale=rationale,
        confidence=confidence,
        policy_id=policy_id,
        decision_authority=decision_authority,
    )

    return store.write_artifact(
        kind="certification_decision",
        artifact_id=decision.certification_id,
        payload=decision.to_dict(),
    )
```

---

# 18. `src/tiannara/cli.py`

```python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .audit import audit_isr
from .candidates import create_candidate, register_backend
from .certification import certify_candidate
from .errors import TiannaraError
from .evidence import EvidenceLedger
from .hashing import hash_obj
from .models import BackendContract, ISRManifest, Requirement
from .requirements import build_graph
from .store import Store
from .traceability import TraceabilityStore


def _store(args: argparse.Namespace) -> Store:
    store = Store(Path(args.root))
    store.ensure()
    return store


def cmd_init(args: argparse.Namespace) -> None:
    store = _store(args)
    print(
        json.dumps(
            {
                "status": "initialized",
                "root": str(store.root),
            },
            indent=2,
        )
    )


def cmd_demo(args: argparse.Namespace) -> None:
    store = _store(args)
    trace = TraceabilityStore(store)
    ledger = EvidenceLedger(store)

    requirement_1 = Requirement(
        requirement_id="REQ-DEMO-001",
        title="A user can create a task",
        source="phase0-demo",
        type="FUNCTIONAL",
        priority="MUST",
        epistemic_status="KNOWN",
        acceptance_criteria=[
            "Given valid task data, when create task is invoked, then a task is created"
        ],
        verification_strategy=["api_test"],
        isr_mappings=["create_task"],
    )

    requirement_2 = Requirement(
        requirement_id="REQ-DEMO-002",
        title="A user can list tasks",
        source="phase0-demo",
        type="FUNCTIONAL",
        priority="MUST",
        epistemic_status="KNOWN",
        acceptance_criteria=[
            "Given existing tasks, when list tasks is invoked, then tasks are returned"
        ],
        verification_strategy=["api_test"],
        isr_mappings=["list_tasks"],
    )

    graph = build_graph(
        graph_id="REQGRAPH-DEMO-001",
        version="1.0.0",
        requirements=[requirement_1, requirement_2],
        edges=[],
        created_by="phase0-demo",
    )

    graph_envelope = store.write_artifact(
        kind="requirement_graph",
        artifact_id=graph.graph_id,
        payload=graph.to_dict(),
    )

    isr = ISRManifest(
        isr_id="ISR-DEMO-001",
        version="1.0.0",
        requirement_graph_hash=graph_envelope["content_hash"],
        domains=["task_management"],
        capabilities=["create_task", "list_tasks"],
        entities=[
            {
                "name": "Task",
                "attributes": [
                    {"name": "id", "type": "identifier"},
                    {"name": "title", "type": "text"},
                    {"name": "status", "type": "enumeration"},
                ],
            }
        ],
        aggregates=["Task"],
        workflows=["task_creation", "task_listing"],
        commands=["CreateTask"],
        queries=["ListTasks"],
        events=["TaskCreated"],
        interfaces=[
            {
                "name": "TaskApi",
                "operations": ["CreateTask", "ListTasks"],
            }
        ],
        security_policies=["authenticate_requests", "authorize_task_access"],
        performance_constraints=["p95_latency_under_200ms"],
        deployment_constraints=["container_deployable"],
        observability_requirements=["structured_logs", "metrics", "health_checks"],
        assumptions=["single_region_deployment"],
        unresolved_questions=[],
        metadata={
            "category": "CRUD SaaS",
            "architectural_risks": ["single_node_persistence"],
        },
        created_by="phase0-demo",
    )

    isr_envelope = store.write_artifact(
        kind="isr",
        artifact_id=isr.isr_id,
        payload=isr.to_dict(),
    )

    trace.add_link(
        source_id=requirement_1.requirement_id,
        target_id=isr.isr_id,
        relation_type="REQUIREMENT_TO_ISR",
        created_by="phase0-demo",
    )

    trace.add_link(
        source_id=requirement_2.requirement_id,
        target_id=isr.isr_id,
        relation_type="REQUIREMENT_TO_ISR",
        created_by="phase0-demo",
    )

    audit = audit_isr(
        isr_envelope=isr_envelope,
        graph_envelope=graph_envelope,
        trace_store=trace,
        auditor_identity="phase0-auditor",
    )

    if audit.status != "AUDITED":
        raise TiannaraError(f"ISR audit rejected: {audit.invariant_report}")

    audit_envelope = store.write_artifact(
        kind="isr_audit",
        artifact_id=audit.audit_id,
        payload=audit.to_dict(),
    )

    backend = BackendContract(
        backend_id="reference-backend",
        backend_version="0.0.1",
        backend_type="backend",
        supported_isr_capabilities=["create_task", "list_tasks"],
        supported_workload_categories=["crud_saas"],
        target_platform="reference",
        dependencies=[],
        verification_capabilities=["unit", "integration"],
        security_characteristics=["least_privilege"],
        deployment_targets=["local"],
        observability_capabilities=["structured_logs"],
        limitations=["Phase 0 reference backend only"],
        status="ACTIVE",
        created_by="phase0-demo",
    )

    backend_envelope = register_backend(store, backend)

    genome = {
        "architecture_style": "modular_monolith",
        "persistence_capability": "repository",
        "messaging_capability": "none",
    }

    candidate_envelope = create_candidate(
        store,
        isr_envelope=isr_envelope,
        backend_envelope=backend_envelope,
        genome_hash=hash_obj(genome),
        artifact_identity="ARTIFACT-DEMO-0001",
        changed_dimensions=["backend"],
        unchanged_dimensions=["isr"],
        hypothesis="The reference backend can compile the demo ISR.",
        expected_outcome="Compilation and tests produce passing evidence.",
        measurement_strategy="Phase 0 evidence ledger checks.",
        acceptance_criteria="All required evidence entries are PASS.",
        falsifier="Any FAIL or ERROR evidence entry.",
        novelty_proof="Initial Phase 0 reference candidate.",
    )

    artifact_hashes = {
        candidate_envelope["id"]: candidate_envelope["content_hash"],
        isr_envelope["id"]: isr_envelope["content_hash"],
    }

    evidence_1 = ledger.append(
        trial_id="TRIAL-DEMO-001",
        stage="compilation",
        subject_type="candidate",
        subject_id=candidate_envelope["id"],
        result="PASS",
        artifact_hashes=artifact_hashes,
        environment={"phase": "0"},
        compiler_versions={"tiannara": "0.0.1"},
        backend_versions={backend.backend_id: backend.backend_version},
        configuration={"mode": "demo"},
        seed="demo",
    )

    evidence_2 = ledger.append(
        trial_id="TRIAL-DEMO-001",
        stage="test",
        subject_type="candidate",
        subject_id=candidate_envelope["id"],
        result="PASS",
        artifact_hashes=artifact_hashes,
        environment={"phase": "0"},
        compiler_versions={"tiannara": "0.0.1"},
        backend_versions={backend.backend_id: backend.backend_version},
        configuration={"mode": "demo"},
        seed="demo",
    )

    certification_envelope = certify_candidate(
        store,
        ledger,
        subject_type="candidate",
        subject_id=candidate_envelope["id"],
        isr_id=isr.isr_id,
        candidate_id=candidate_envelope["id"],
        backend_id=backend.backend_id,
        artifact_id="ARTIFACT-DEMO-0001",
        audit_id=audit_envelope["id"],
        evidence_ids=[evidence_1["evidence_id"], evidence_2["evidence_id"]],
        decision_authority="phase0-cli",
        rationale="Phase 0 demonstration pipeline passed all required checks.",
        confidence=1.0,
    )

    print(
        json.dumps(
            {
                "status": "demo_complete",
                "requirement_graph": graph_envelope["id"],
                "isr": isr_envelope["id"],
                "isr_hash": isr_envelope["content_hash"],
                "audit": audit_envelope["id"],
                "audit_status": audit_envelope["payload"]["status"],
                "backend": backend_envelope["id"],
                "candidate": candidate_envelope["id"],
                "certification": certification_envelope["id"],
            },
            indent=2,
        )
    )


def cmd_verify_evidence(args: argparse.Namespace) -> None:
    store = _store(args)
    ledger = EvidenceLedger(store)
    ledger.verify()

    print(
        json.dumps(
            {
                "status": "evidence_ledger_ok",
                "entries": len(ledger.entries()),
            },
            indent=2,
        )
    )


def cmd_show_artifact(args: argparse.Namespace) -> None:
    store = _store(args)
    artifact = store.read_artifact(args.kind, args.artifact_id)
    print(json.dumps(artifact, indent=2, sort_keys=True))


def main(argv=None) -> int:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--root",
        default="./var/tiannara",
        help="Tiannara Phase 0 workspace root",
    )

    parser = argparse.ArgumentParser(
        prog="tiannara",
        description="Tiannara Phase 0 constitutional kernel reference runtime",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    parser_init = subparsers.add_parser("init", parents=[common])
    parser_init.set_defaults(func=cmd_init)

    parser_demo = subparsers.add_parser("demo", parents=[common])
    parser_demo.set_defaults(func=cmd_demo)

    parser_verify_evidence = subparsers.add_parser("verify-evidence", parents=[common])
    parser_verify_evidence.set_defaults(func=cmd_verify_evidence)

    parser_show_artifact = subparsers.add_parser("show-artifact", parents=[common])
    parser_show_artifact.add_argument("kind")
    parser_show_artifact.add_argument("artifact_id")
    parser_show_artifact.set_defaults(func=cmd_show_artifact)

    args = parser.parse_args(argv)

    try:
        args.func(args)
        return 0
    except TiannaraError as exc:
        print(
            json.dumps(
                {
                    "status": "error",
                    "type": exc.__class__.__name__,
                    "message": str(exc),
                },
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1
    except FileNotFoundError as exc:
        print(
            json.dumps(
                {
                    "status": "error",
                    "type": "FileNotFoundError",
                    "message": str(exc),
                },
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
```

---

# 19. `tests/test_phase0.py`

```python
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tiannara.audit import audit_isr
from tiannara.candidates import create_candidate, register_backend
from tiannara.certification import certify_candidate
from tiannara.errors import (
    CertificationError,
    EvidenceError,
    NoOpEvolutionError,
)
from tiannara.evidence import EvidenceLedger
from tiannara.hashing import hash_obj
from tiannara.models import BackendContract, ISRManifest, Requirement
from tiannara.requirements import build_graph
from tiannara.store import Store
from tiannara.traceability import TraceabilityStore


class Phase0TestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = Path(tempfile.mkdtemp(prefix="tiannara-phase0-"))
        self.store = Store(self.directory)
        self.store.ensure()
        self.trace = TraceabilityStore(self.store)
        self.ledger = EvidenceLedger(self.store)

    def tearDown(self) -> None:
        shutil.rmtree(self.directory, ignore_errors=True)

    def _requirement(self, requirement_id: str, title: str) -> Requirement:
        return Requirement(
            requirement_id=requirement_id,
            title=title,
            source="test",
            type="FUNCTIONAL",
            priority="MUST",
            epistemic_status="KNOWN",
        )

    def _graph_envelope(self, requirements):
        graph = build_graph(
            graph_id="REQGRAPH-TEST",
            version="1.0.0",
            requirements=requirements,
            edges=[],
            created_by="test",
        )

        return self.store.write_artifact(
            kind="requirement_graph",
            artifact_id=graph.graph_id,
            payload=graph.to_dict(),
        )

    def _isr(self, requirement_graph_hash: str, capabilities=None) -> ISRManifest:
        return ISRManifest(
            isr_id="ISR-TEST",
            version="1.0.0",
            requirement_graph_hash=requirement_graph_hash,
            domains=["test_domain"],
            capabilities=capabilities or ["capability_a"],
            entities=[
                {
                    "name": "Thing",
                    "attributes": [
                        {"name": "id", "type": "identifier"},
                    ],
                }
            ],
            aggregates=["Thing"],
            workflows=["thing_flow"],
            commands=["DoThing"],
            queries=["GetThing"],
            events=["ThingDone"],
            interfaces=[
                {
                    "name": "ThingApi",
                    "operations": ["DoThing", "GetThing"],
                }
            ],
            security_policies=["authenticate_requests"],
            performance_constraints=["p95_latency_under_200ms"],
            deployment_constraints=["container_deployable"],
            observability_requirements=["structured_logs"],
            assumptions=["test_assumption"],
            unresolved_questions=[],
            metadata={
                "category": "test",
                "architectural_risks": [],
            },
            created_by="test",
        )

    def _isr_envelope(self, requirement_graph_hash: str, capabilities=None):
        isr = self._isr(requirement_graph_hash, capabilities)
        return self.store.write_artifact(
            kind="isr",
            artifact_id=isr.isr_id,
            payload=isr.to_dict(),
        )

    def _backend_envelope(self):
        backend = BackendContract(
            backend_id="reference-backend",
            backend_version="0.0.1",
            backend_type="backend",
            supported_isr_capabilities=["capability_a"],
            supported_workload_categories=["test"],
            target_platform="reference",
            dependencies=[],
            verification_capabilities=["unit"],
            security_characteristics=["least_privilege"],
            deployment_targets=["local"],
            observability_capabilities=["structured_logs"],
            limitations=["test backend"],
            status="ACTIVE",
            created_by="test",
        )

        return register_backend(self.store, backend)

    def _setup_candidate(self):
        requirements = [
            self._requirement("REQ-1", "Requirement one"),
            self._requirement("REQ-2", "Requirement two"),
        ]

        graph_envelope = self._graph_envelope(requirements)
        isr_envelope = self._isr_envelope(graph_envelope["content_hash"])

        for requirement in requirements:
            self.trace.add_link(
                source_id=requirement.requirement_id,
                target_id=isr_envelope["payload"]["isr_id"],
                relation_type="REQUIREMENT_TO_ISR",
                created_by="test",
            )

        audit = audit_isr(
            isr_envelope=isr_envelope,
            graph_envelope=graph_envelope,
            trace_store=self.trace,
            auditor_identity="test-auditor",
        )

        audit_envelope = self.store.write_artifact(
            kind="isr_audit",
            artifact_id=audit.audit_id,
            payload=audit.to_dict(),
        )

        backend_envelope = self._backend_envelope()
        genome_hash = hash_obj({"architecture": "modular_monolith"})

        candidate_envelope = create_candidate(
            self.store,
            isr_envelope=isr_envelope,
            backend_envelope=backend_envelope,
            genome_hash=genome_hash,
            artifact_identity="ARTIFACT-TEST-1",
            changed_dimensions=["backend"],
            unchanged_dimensions=["isr"],
            hypothesis="hypothesis",
            expected_outcome="expected outcome",
            measurement_strategy="measurement strategy",
            acceptance_criteria="acceptance criteria",
            falsifier="falsifier",
            novelty_proof="novelty proof",
        )

        return {
            "requirements": requirements,
            "graph_envelope": graph_envelope,
            "isr_envelope": isr_envelope,
            "audit_envelope": audit_envelope,
            "backend_envelope": backend_envelope,
            "candidate_envelope": candidate_envelope,
            "genome_hash": genome_hash,
        }

    def test_canonical_hash_is_stable(self) -> None:
        left = {"a": 1, "b": [1, 2, 3], "c": {"x": True}}
        right = {"b": [1, 2, 3], "a": 1, "c": {"x": True}}

        self.assertEqual(hash_obj(left), hash_obj(right))

    def test_audit_passes_with_traceability_and_clean_isr(self) -> None:
        context = self._setup_candidate()

        self.assertEqual(
            context["audit_envelope"]["payload"]["status"],
            "AUDITED",
        )

    def test_audit_rejects_implementation_leakage(self) -> None:
        requirements = [self._requirement("REQ-1", "Requirement one")]
        graph_envelope = self._graph_envelope(requirements)

        isr_envelope = self._isr_envelope(
            graph_envelope["content_hash"],
            capabilities=["postgres"],
        )

        self.trace.add_link(
            source_id=requirements[0].requirement_id,
            target_id=isr_envelope["payload"]["isr_id"],
            relation_type="REQUIREMENT_TO_ISR",
            created_by="test",
        )

        audit = audit_isr(
            isr_envelope=isr_envelope,
            graph_envelope=graph_envelope,
            trace_store=self.trace,
            auditor_identity="test-auditor",
        )

        self.assertEqual(audit.status, "REJECTED")
        self.assertIn("implementation_leakage", audit.invariant_report["issues"])
        self.assertFalse(audit.leakage_report["clean"])

    def test_audit_rejects_missing_traceability(self) -> None:
        requirements = [self._requirement("REQ-1", "Requirement one")]
        graph_envelope = self._graph_envelope(requirements)
        isr_envelope = self._isr_envelope(graph_envelope["content_hash"])

        audit = audit_isr(
            isr_envelope=isr_envelope,
            graph_envelope=graph_envelope,
            trace_store=self.trace,
            auditor_identity="test-auditor",
        )

        self.assertEqual(audit.status, "REJECTED")
        self.assertIn("missing_traceability", audit.invariant_report["issues"])

    def test_noop_evolution_is_rejected(self) -> None:
        context = self._setup_candidate()

        with self.assertRaises(NoOpEvolutionError):
            create_candidate(
                self.store,
                isr_envelope=context["isr_envelope"],
                backend_envelope=context["backend_envelope"],
                genome_hash=context["genome_hash"],
                artifact_identity="ARTIFACT-TEST-1",
                changed_dimensions=["backend"],
                unchanged_dimensions=["isr"],
                hypothesis="child hypothesis",
                expected_outcome="child outcome",
                measurement_strategy="child measurement",
                acceptance_criteria="child acceptance",
                falsifier="child falsifier",
                novelty_proof="child novelty",
                parent_candidate_id=context["candidate_envelope"]["id"],
            )

    def test_evidence_ledger_detects_tampering(self) -> None:
        self.ledger.append(
            trial_id="TRIAL-TEST",
            stage="test",
            subject_type="candidate",
            subject_id="candidate_x",
            result="PASS",
        )

        self.assertTrue(self.ledger.verify())

        ledger_path = self.store.root / "evidence" / "ledger.jsonl"
        lines = ledger_path.read_text(encoding="utf-8").strip().splitlines()
        entry = json.loads(lines[0])
        entry["stage"] = "tampered"
        ledger_path.write_text(
            json.dumps(entry, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )

        with self.assertRaises(EvidenceError):
            self.ledger.verify()

    def test_certification_requires_passing_evidence(self) -> None:
        context = self._setup_candidate()

        failing_evidence = self.ledger.append(
            trial_id="TRIAL-TEST",
            stage="test",
            subject_type="candidate",
            subject_id=context["candidate_envelope"]["id"],
            result="FAIL",
        )

        with self.assertRaises(CertificationError):
            certify_candidate(
                self.store,
                self.ledger,
                subject_type="candidate",
                subject_id=context["candidate_envelope"]["id"],
                isr_id=context["isr_envelope"]["payload"]["isr_id"],
                candidate_id=context["candidate_envelope"]["id"],
                backend_id=context["backend_envelope"]["id"],
                artifact_id="ARTIFACT-TEST-1",
                audit_id=context["audit_envelope"]["id"],
                evidence_ids=[failing_evidence["evidence_id"]],
                decision_authority="test",
            )

    def test_certification_succeeds_with_passing_evidence(self) -> None:
        context = self._setup_candidate()

        evidence_one = self.ledger.append(
            trial_id="TRIAL-TEST",
            stage="compilation",
            subject_type="candidate",
            subject_id=context["candidate_envelope"]["id"],
            result="PASS",
        )

        evidence_two = self.ledger.append(
            trial_id="TRIAL-TEST",
            stage="test",
            subject_type="candidate",
            subject_id=context["candidate_envelope"]["id"],
            result="PASS",
        )

        certification_envelope = certify_candidate(
            self.store,
            self.ledger,
            subject_type="candidate",
            subject_id=context["candidate_envelope"]["id"],
            isr_id=context["isr_envelope"]["payload"]["isr_id"],
            candidate_id=context["candidate_envelope"]["id"],
            backend_id=context["backend_envelope"]["id"],
            artifact_id="ARTIFACT-TEST-1",
            audit_id=context["audit_envelope"]["id"],
            evidence_ids=[evidence_one["evidence_id"], evidence_two["evidence_id"]],
            decision_authority="test",
        )

        self.assertEqual(
            certification_envelope["payload"]["decision"],
            "CERTIFIED",
        )


if __name__ == "__main__":
    unittest.main()
```

---

# Installation and Execution

From the `tiannara-phase0/` directory:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Run the Phase 0 tests:

```bash
python -m unittest discover -s tests -v
```

Initialize the workspace:

```bash
tiannara --root ./var/tiannara init
```

Run the full Phase 0 demonstration pipeline:

```bash
tiannara --root ./var/tiannara demo
```

Verify the evidence ledger:

```bash
tiannara --root ./var/tiannara verify-evidence
```

Inspect artifacts:

```bash
tiannara --root ./var/tiannara show-artifact isr ISR-DEMO-001
tiannara --root ./var/tiannara show-artifact candidate <candidate_id>
tiannara --root ./var/tiannara show-artifact certification_decision <certification_id>
```

---

# Phase 0 Response Contract

## Objective

Provide a runnable Phase 0 constitutional kernel for Tiannara.

## Current Architecture

Implemented as a minimal Python reference runtime with:

- filesystem artifact store
- canonical hashing
- requirement graph construction
- ISR manifest modeling
- ISR audit
- implementation leakage detection
- traceability links
- backend contract registration
- candidate creation with no-op rejection
- append-only evidence ledger
- certification gate

## Requirements Covered

Phase 0 covers:

- ISR-first modeling
- requirement graph construction
- ISR audit before compilation
- implementation leakage rejection
- traceability from requirement to ISR
- immutable evidence chain
- certification requiring passing evidence
- no-op evolution rejection

## Decisions

- Python is used only as a Phase 0 reference implementation.
- JSON artifacts are used as the portable storage format.
- Canonical JSON is used for deterministic hashing.
- Evidence is append-only.
- Certification is denied without passing audit and passing evidence.
- No generated application code is produced in Phase 0.

## Changed Files

All files listed above are new.

## Contracts

Introduced contracts:

- `Requirement`
- `RequirementGraph`
- `ISRManifest`
- `ISRAudit`
- `TraceabilityLink`
- `BackendContract`
- `Candidate`
- `Evidence`
- `CertificationDecision`

## ISR Changes

Initial ISR manifest model is implemented.

No production ISR is yet certified.

## Tests

Included tests cover:

- canonical hash stability
- ISR audit pass path
- ISR leakage rejection
- missing traceability rejection
- no-op evolution rejection
- evidence tamper detection
- certification failure on failing evidence
- certification success on passing evidence

## Verification

Run:

```bash
python -m unittest discover -s tests -v
```

## Certification

This Phase 0 runtime is not itself certified.

## Evidence

No external runtime evidence exists yet. Local tests and demo execution produce evidence.

## Risks

- Filesystem store is simple and not production-hardened.
- Leakage detection is heuristic and needs expansion.
- ISR schema is minimal and must evolve carefully.
- No real compiler backend exists yet.
- No deployment or observability runtime exists yet.

## Limitations

This is not yet the full Tiannara platform.

It does not yet include:

- full evolution engine
- Pareto fitness evaluation
- real compiler backends
- generated frontend/backend artifacts
- deployment compiler
- runtime telemetry
- portfolio exemplars

## Evolution Implications

This kernel creates the constitutional base required before adding:

- compiler backends
- architecture candidate evolution
- fitness evaluation
- full-stack generation
- deployment pipelines
- production learning loops

## Next Architectural Step

The next phase should be:

**Phase 1 — Requirement Graph + ISR Core Expansion**

That phase should add:

- richer requirement taxonomy
- explicit UNKNOWN / ASSUMED / INFERRED / REQUIRED_DECISION workflows
- stronger ISR schema validation
- ISR versioning
- requirement-to-ISR coverage reports
- traceability queries
- JSON Schema exports for all Phase 0 contracts.