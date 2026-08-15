"""Phase-31 corpus generator: deterministic, stratified SystemModel synthesis.

Produces a calibration corpus *without* LLM invocation, so backend-correctness
measurement stays hermetic and fast. Each generated ``SystemModel`` is built
directly against the typed ISR contract (``system_model.py``) -- never against
the hand-reconstructed proposal sketch -- so the validity test is a true
reconciliation signal against the tree.

Stratification axes (every stratum cycles, guaranteeing full enum/field coverage
in a finite corpus):
    * topology / availability / scaling        -> InfrastructureModel
    * auth / authz / data-classification       -> SecurityModel
    * consistency posture                      -> DataModelSpec.consistency
    * rollout / scaling-policy                 -> DeploymentModel
    * communication styles (4) x capability-set -> ServiceSpec / BusinessCapability
    * field-type coverage (all 10 AbstractFieldType values) -> FieldSpec set
    * service count 1..3 (+events for event-driven) -> services / events wiring

Determinism: seeded ``random.Random``; system identity is content-addressable via
``graph_hash`` (sha256 of the slug). Reproducibility is asserted in the tests.
"""
from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from enum import Enum
from typing import Iterator, Optional

from tiannara.domain.models.system_model import (
    AbstractFieldType,
    AuthenticationPosture,
    AuthorizationModel,
    BusinessCapability,
    Criticality,
    CommunicationStyle,
    EventSpec,
    EventOrdering,
    DeliverySemantics,
    ConsistencyPosture,
    DataClassification,
    DataModelSpec,
    DomainSpec,
    FieldSpec,
    Priority,
    RequirementsReference,
    SecurityModel,
    ServiceSpec,
    SystemModel,
    AvailabilityPosture,
    DeploymentModel,
    InfrastructureModel,
    RolloutStrategy,
    ScalingPolicy,
    ScalingUnit,
    TopologyStyle,
)

__all__ = [
    "SystemModelCorpusGenerator",
    "CorpusSpec",
    "FieldOrder",
    "generate_corpus",
    "DEFAULT_GENERATED_CORPUS_SIZE",
]

DEFAULT_GENERATED_CORPUS_SIZE = 50


class FieldOrder(str, Enum):
    """How data-model fields are ordered within a generated SystemModel.

    The FastAPI backend emits Python function signatures from data-model
    fields; an ISR whose optional field precedes a required field is *valid ISR*
    but yields a ``SyntaxError`` unless the backend reorders at emission. This
    switch lets calibration measure that defect honestly:

      * REQUIRED_FIRST (default) -- generator pre-orders; biased corpus that
        hides the backend bug. Backwards compatible with today's suite.
      * UNRESTRICTED  -- seeded shuffle; statistically unbiased sampling.
      * OPTIONAL_FIRST -- deterministic adversarial ordering; guarantees the
        field-order defect is triggered on every model.
    """

    REQUIRED_FIRST = "required_first"
    UNRESTRICTED = "unrestricted"
    OPTIONAL_FIRST = "optional_first"


@dataclass(frozen=True)
class CorpusSpec:
    """Parameters for a stratified corpus generation run."""

    size: int = DEFAULT_GENERATED_CORPUS_SIZE
    seed: int = 0
    field_order: FieldOrder = FieldOrder.REQUIRED_FIRST

# --------------------------------------------------------------------------
# Technology-token-safe domain vocabulary (kept clear of the ISR denylist):
# no "python"/"redis"/"docker"/"aws"/"fastapi"/"postgres"/etc.
# --------------------------------------------------------------------------
_DOMAIN_NOUNS = (
    "Order", "Inventory", "Notification", "Payment", "Subscription",
    "Reservation", "Scheduling", "Analytics", "Billing", "Shipping",
    "Loyalty", "Catalog", "Account", "Feature", "Incident",
)

# Field profiles rotate to guarantee every AbstractFieldType is exercised.
_PROFILE_FULL = (
    ("id", AbstractFieldType.IDENTIFIER),
    ("name", AbstractFieldType.TEXT),
    ("quantity", AbstractFieldType.INTEGER),
    ("price", AbstractFieldType.DECIMAL),
    ("active", AbstractFieldType.BOOLEAN),
    ("occurred_at", AbstractFieldType.TIMESTAMP),
    ("status", AbstractFieldType.ENUMERATION),
    ("owner_id", AbstractFieldType.REFERENCE),
    ("payload", AbstractFieldType.DOCUMENT),
    ("attachment", AbstractFieldType.BINARY),
)
_PROFILE_RICH = (
    ("id", AbstractFieldType.IDENTIFIER),
    ("name", AbstractFieldType.TEXT),
    ("quantity", AbstractFieldType.INTEGER),
    ("price", AbstractFieldType.DECIMAL),
)
_PROFILE_CORE = (
    ("id", AbstractFieldType.IDENTIFIER),
    ("name", AbstractFieldType.TEXT),
    ("quantity", AbstractFieldType.INTEGER),
)
_PROFILE_SKELETON = (
    ("id", AbstractFieldType.IDENTIFIER),
    ("name", AbstractFieldType.TEXT),
)
_FIELD_PROFILES = (_PROFILE_SKELETON, _PROFILE_CORE, _PROFILE_RICH, _PROFILE_FULL)

# Communication-style sets per stratum (covers SYNC/ASYNC/BATCH/STREAMING).
_COMM_SETS = (
    (CommunicationStyle.SYNCHRONOUS_REQUEST_RESPONSE,),
    (CommunicationStyle.ASYNCHRONOUS_EVENT,),
    (CommunicationStyle.SYNCHRONOUS_REQUEST_RESPONSE, CommunicationStyle.ASYNCHRONOUS_EVENT),
    (CommunicationStyle.ASYNCHRONOUS_EVENT, CommunicationStyle.STREAMING),
    (CommunicationStyle.SYNCHRONOUS_REQUEST_RESPONSE, CommunicationStyle.BATCH, CommunicationStyle.STREAMING),
    (CommunicationStyle.STREAMING,),
    (CommunicationStyle.BATCH, CommunicationStyle.ASYNCHRONOUS_EVENT),
)

# Architectural stances -- each is a deterministic, enum-covering stratum.
_STRATA = (
    {
        "topology": TopologyStyle.MODULAR_MONOLITH,
        "availability": AvailabilityPosture.MULTI_ZONE,
        "scaling_unit": ScalingUnit.INSTANCE,
        "auth": AuthenticationPosture.TOKEN_BASED,
        "authz": AuthorizationModel.RBAC,
        "data_classification": DataClassification.INTERNAL,
        "consistency": ConsistencyPosture.STRONG,
        "rollout": RolloutStrategy.ROLLING,
        "scaling_policy": ScalingPolicy.REACTIVE,
        "comm": _COMM_SETS[0],
    },
    {
        "topology": TopologyStyle.SINGLE_SERVICE,
        "availability": AvailabilityPosture.SINGLE_ZONE,
        "scaling_unit": ScalingUnit.SERVICE,
        "auth": AuthenticationPosture.ANONYMOUS,
        "authz": AuthorizationModel.NONE,
        "data_classification": DataClassification.PUBLIC,
        "consistency": ConsistencyPosture.EVENTUAL,
        "rollout": RolloutStrategy.ALL_AT_ONCE,
        "scaling_policy": ScalingPolicy.STATIC,
        "comm": _COMM_SETS[1],
    },
    {
        "topology": TopologyStyle.EVENT_DRIVEN,
        "availability": AvailabilityPosture.MULTI_REGION,
        "scaling_unit": ScalingUnit.PARTITION,
        "auth": AuthenticationPosture.FEDERATED_IDENTITY,
        "authz": AuthorizationModel.ABAC,
        "data_classification": DataClassification.CONFIDENTIAL,
        "consistency": ConsistencyPosture.CAUSAL,
        "rollout": RolloutStrategy.BLUE_GREEN,
        "scaling_policy": ScalingPolicy.PREDICTIVE,
        "comm": _COMM_SETS[2],
    },
    {
        "topology": TopologyStyle.HYBRID,
        "availability": AvailabilityPosture.MULTI_REGION,
        "scaling_unit": ScalingUnit.INSTANCE,
        "auth": AuthenticationPosture.MUTUAL_AUTHENTICATION,
        "authz": AuthorizationModel.POLICY_BASED,
        "data_classification": DataClassification.RESTRICTED,
        "consistency": ConsistencyPosture.STRONG,
        "rollout": RolloutStrategy.CANARY,
        "scaling_policy": ScalingPolicy.REACTIVE,
        "comm": _COMM_SETS[3],
    },
    {
        "topology": TopologyStyle.DISTRIBUTED_SERVICES,
        "availability": AvailabilityPosture.MULTI_ZONE,
        "scaling_unit": ScalingUnit.PARTITION,
        "auth": AuthenticationPosture.CREDENTIAL_BASED,
        "authz": AuthorizationModel.RBAC,
        "data_classification": DataClassification.INTERNAL,
        "consistency": ConsistencyPosture.EVENTUAL,
        "rollout": RolloutStrategy.ROLLING,
        "scaling_policy": ScalingPolicy.STATIC,
        "comm": _COMM_SETS[5],
    },
    {
        "topology": TopologyStyle.MODULAR_MONOLITH,
        "availability": AvailabilityPosture.SINGLE_ZONE,
        "scaling_unit": ScalingUnit.SERVICE,
        "auth": AuthenticationPosture.TOKEN_BASED,
        "authz": AuthorizationModel.ABAC,
        "data_classification": DataClassification.CONFIDENTIAL,
        "consistency": ConsistencyPosture.CAUSAL,
        "rollout": RolloutStrategy.CANARY,
        "scaling_policy": ScalingPolicy.PREDICTIVE,
        "comm": _COMM_SETS[4],
    },
    {
        "topology": TopologyStyle.EVENT_DRIVEN,
        "availability": AvailabilityPosture.MULTI_REGION,
        "scaling_unit": ScalingUnit.INSTANCE,
        "auth": AuthenticationPosture.ANONYMOUS,
        "authz": AuthorizationModel.NONE,
        "data_classification": DataClassification.PUBLIC,
        "consistency": ConsistencyPosture.STRONG,
        "rollout": RolloutStrategy.BLUE_GREEN,
        "scaling_policy": ScalingPolicy.REACTIVE,
        "comm": _COMM_SETS[6],
    },
    {
        "topology": TopologyStyle.HYBRID,
        "availability": AvailabilityPosture.MULTI_ZONE,
        "scaling_unit": ScalingUnit.PARTITION,
        "auth": AuthenticationPosture.FEDERATED_IDENTITY,
        "authz": AuthorizationModel.POLICY_BASED,
        "data_classification": DataClassification.RESTRICTED,
        "consistency": ConsistencyPosture.EVENTUAL,
        "rollout": RolloutStrategy.ALL_AT_ONCE,
        "scaling_policy": ScalingPolicy.STATIC,
        "comm": _COMM_SETS[3],
    },
)

_CRIT = (Criticality.CORE, Criticality.SUPPORTING, Criticality.GENERIC)
_PRIO = (Priority.MUST, Priority.SHOULD, Priority.COULD)


def _slug_from_name(system_name: str) -> str:
    """Reproduce the harness slug contract: lowercase, non-alnum -> '-'."""
    out = "".join(ch if ch.isalnum() else "-" for ch in system_name.lower())
    return "-".join(p for p in out.split("-") if p)


class SystemModelCorpusGenerator:
    """Deterministic generator of varied, validation-safe SystemModels."""

    def __init__(
        self,
        spec: Optional[CorpusSpec] = None,
        *,
        seed: int = 0,
        size: Optional[int] = None,
        field_order: FieldOrder = FieldOrder.REQUIRED_FIRST,
    ) -> None:
        if isinstance(spec, CorpusSpec):
            self.spec = spec
        else:
            self.spec = CorpusSpec(
                size=size if size is not None else DEFAULT_GENERATED_CORPUS_SIZE,
                seed=seed,
                field_order=field_order,
            )

    def generate(self, count: Optional[int] = None) -> list[SystemModel]:
        n = count if count is not None else self.spec.size
        rng = random.Random(self.spec.seed)
        models: list[SystemModel] = []
        existing: set[str] = set()
        for i in range(n):
            model = self._build_model(i, rng, existing)
            models.append(model)
            existing.add(model.system_name)
        return models

    def __iter__(self) -> Iterator[SystemModel]:
        return iter(self.generate(self.spec.size))

    # -- model assembly -------------------------------------------------------

    def _build_model(self, index: int, rng: random.Random, existing: set[str]) -> SystemModel:
        stratum = _STRATA[index % len(_STRATA)]
        field_profile = _FIELD_PROFILES[index % len(_FIELD_PROFILES)]
        noun = _DOMAIN_NOUNS[index % len(_DOMAIN_NOUNS)]
        system_name = self._unique_name(rng, noun, index, existing)

        slug = _slug_from_name(system_name)
        graph_hash = hashlib.sha256(system_name.encode("utf-8")).hexdigest()[:16]

        service_count = self._service_count(stratum["topology"])
        domain = DomainSpec(
            id="general",
            name="General",
            description=f"General domain for the {system_name.lower()}",
            capability_ids=[f"cap-{slug}-{j}" for j in range(service_count)],
            ubiquitous_language={
                "entity": "a thing being tracked",
                "status": "lifecycle marker for an entity",
            },
        )

        services: list[ServiceSpec] = []
        capabilities: list[BusinessCapability] = []
        for j in range(service_count):
            svc_id = f"svc-{slug}-{j}"
            cap_id = f"cap-{slug}-{j}"
            services.append(
                ServiceSpec(
                    id=svc_id,
                    name=f"{noun} {j + 1}",
                    domain_id="general",
                    responsibilities=[
                        f"Owns the {noun.lower()} lifecycle",
                        f"Exposes the {noun.lower()} capability",
                    ],
                    exposed_capability_ids=[cap_id],
                    communication_styles=list(stratum["comm"]),
                )
            )
            capabilities.append(
                BusinessCapability(
                    id=cap_id,
                    name=f"{noun} {j + 1} Capability",
                    description=f"Support for the {noun.lower()} workflow",
                    criticality=_CRIT[(index + j) % len(_CRIT)],
                    priority=_PRIO[(index + j) % len(_PRIO)],
                    traced_requirement_ids=[f"req-{slug}-{j}"],
                )
            )

        primary_svc = services[0].id if services else f"svc-{slug}-0"
        raw_fields = [
            self._field(f_name, f_type, index, j)
            for j, (f_name, f_type) in enumerate(field_profile)
        ]
        model = DataModelSpec(
            id=f"dm-{slug}",
            name=self._safe_model_name(noun),
            owning_service_id=primary_svc,
            fields=self._order_fields(raw_fields, rng),
            invariants=[
                f"{noun.lower()} id is unique within scope",
                f"{noun.lower()} lifecycle status transitions are monotonic",
            ],
            consistency=stratum["consistency"],
        )
        data_models: list[DataModelSpec] = [model]
        # Secondary data model when multi-service, owned by a peer service.
        if service_count >= 2:
            secondary_svc = services[1].id
            data_models.append(
                DataModelSpec(
                    id=f"dm-{slug}-secondary",
                    name=self._safe_model_name(noun, suffix="ledger"),
                    owning_service_id=secondary_svc,
                    fields=[
                        FieldSpec(name="id", type=AbstractFieldType.IDENTIFIER),
                        FieldSpec(name="reference_id", type=AbstractFieldType.REFERENCE),
                    ],
                    consistency=stratum["consistency"],
                )
            )

        events = self._build_events(slug, services, model, stratum["topology"])

        return SystemModel(
            system_name=system_name,
            problem_statement=(
                f"Track and coordinate {noun.lower()} state across the {system_name.lower()}"
            ),
            requirements_ref=RequirementsReference(graph_id=f"corpus-{slug}", graph_hash=graph_hash),
            capabilities=capabilities,
            domains=[domain],
            services=services,
            data_models=data_models,
            events=events,
            security=SecurityModel(
                authentication=stratum["auth"],
                authorization=stratum["authz"],
                data_classification=stratum["data_classification"],
            ),
            infrastructure=InfrastructureModel(
                topology=stratum["topology"],
                stateful=bool(rng.random() > 0.5),
                scaling_unit=stratum["scaling_unit"],
                availability=stratum["availability"],
            ),
            deployment=DeploymentModel(
                rollout_strategy=stratum["rollout"],
                scaling_policy=stratum["scaling_policy"],
            ),
            extensions={
                "calibration_seed": int(self.spec.seed),
                "calibration_index": index,
                "stratum": index % len(_STRATA),
            },
        )

    # -- helpers --------------------------------------------------------------

    def _unique_name(self, rng, noun: str, index: int, existing: set[str]) -> str:
        base = f"{noun} System"
        candidate = base if base not in existing else f"{base} {index + 1}"
        if candidate in existing:
            candidate = f"{base} Variant {index + 1}"
            suffix = 0
            while candidate in existing:
                suffix += 1
                candidate = f"{base} Variant {index + 1} {suffix}"
        return candidate

    @staticmethod
    def _safe_model_name(noun: str, suffix: str | None = None) -> str:
        return (noun.lower() + (f"_{suffix}" if suffix else "")).replace(" ", "_")

    def _order_fields(self, fields: list[FieldSpec], rng: random.Random) -> list[FieldSpec]:
        """Order emitted fields according to ``self.spec.field_order``.

        The FastAPI backend now reorders parameters (required-first) at emission,
        so field order in the ISR no longer affects generated-code validity. This
        switch exists purely to shape the *corpus* for honest calibration:

          * REQUIRED_FIRST (default): required fields before optional -- a biased
            baseline that passes even an unfixed backend (back-compat with today's
            suite).
          * UNRESTRICTED: seeded shuffle -- statistically unbiased sampling.
          * OPTIONAL_FIRST: optional (reversed) then required (reversed) -- the
            adversarial mode that deterministically triggers the FastAPI
            field-order defect in an unfixed backend, so calibration measures it.

        No field (including the id) is special-cased: backends identify the id
        field by name, never by position.
        """
        required = [f for f in fields if f.required]
        optional = [f for f in fields if not f.required]
        if self.spec.field_order is FieldOrder.OPTIONAL_FIRST:
            return list(reversed(optional)) + list(reversed(required))
        if self.spec.field_order is FieldOrder.UNRESTRICTED:
            ordered = required + optional
            rng.shuffle(ordered)
            return ordered
        return required + optional

    @staticmethod
    def _field(name: str, field_type: AbstractFieldType, index: int, pos: int) -> FieldSpec:
        if field_type is AbstractFieldType.ENUMERATION:
            return FieldSpec(
                name=name,
                type=field_type,
                required=pos % 2 == 0,
                description=f"enumerated value for {name}",
                enumeration_values=["active", "pending", "closed"],
            )
        if field_type is AbstractFieldType.TIMESTAMP:
            return FieldSpec(
                name=name, type=field_type, required=True, description=f"point in time for {name}"
            )
        return FieldSpec(
            name=name,
            type=field_type,
            required=bool((index + pos) % 2 == 0),
            description=f"value for {name}",
        )

    @staticmethod
    def _service_count(topology: TopologyStyle) -> int:
        if topology is TopologyStyle.SINGLE_SERVICE:
            return 1
        if topology is TopologyStyle.MODULAR_MONOLITH:
            return 1
        if topology is TopologyStyle.EVENT_DRIVEN:
            return 3
        if topology is TopologyStyle.HYBRID:
            return 2
        return 3  # DISTRIBUTED_SERVICES

    def _build_events(
        self, slug: str, services: list[ServiceSpec], model: DataModelSpec, topology
    ) -> list:
        if len(services) < 2 or topology is not TopologyStyle.EVENT_DRIVEN:
            return []
        events = []
        for i in range(1, len(services)):
            producer, consumer = services[i - 1], services[i]
            events.append(
                EventSpec(
                    id=f"evt-{slug}-{i}",
                    name=f"{model.name} changed",
                    producer_service_id=producer.id,
                    consumer_service_ids=[consumer.id],
                    payload_model_id=model.id,
                    delivery_semantics=DeliverySemantics.AT_LEAST_ONCE,
                    ordering=EventOrdering.PARTITION_ORDERED if i % 2 else EventOrdering.NONE,
                )
            )
        return events


def generate_corpus(
    count: int = DEFAULT_GENERATED_CORPUS_SIZE,
    seed: int = 0,
    field_order: FieldOrder = FieldOrder.REQUIRED_FIRST,
) -> list[SystemModel]:
    return SystemModelCorpusGenerator(
        seed=seed, size=count, field_order=field_order
    ).generate()
