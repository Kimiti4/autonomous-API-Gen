"""Phase-31 calibration corpus (hand-authored SystemModels).

A small, deterministic, hermetic corpus of *typed* ISR payloads. Using direct
``SystemModel`` instances (rather than intents compiled through an LLM) keeps
calibration hermetic and makes the compiler-correctness signal independent of
the LLM-replay layer. The corpus is growable: the B1 sampler can inject more
models without changing the harness.

Each entry is a technology-free ISR (no tokens banned by
``scan_for_technology_coupling``): the *design* under test, not a technology
choice.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from tiannara.domain.models.backend_declaration import ArtifactKind  # noqa: F401  (re-exported for corpus authors)
from tiannara.domain.models.capability_manifest import (  # noqa: F401
    BundleCapability,
)
from tiannara.domain.models.system_model import (
    AbstractFieldType,
    AuthenticationPosture,
    BusinessCapability,
    DataClassification,
    DataModelSpec,
    DomainSpec,
    FieldSpec,
    RequirementsReference,
    SecurityModel,
    ServiceSpec,
    SystemModel,
)


def _requirements_ref(system_name: str) -> RequirementsReference:
    return RequirementsReference(
        graph_id=f"corpus-{system_name.lower().replace(' ', '-')}",
        graph_hash="0" * 16,
    )


def _id_field() -> FieldSpec:
    return FieldSpec(name="id", type=AbstractFieldType.IDENTIFIER)


def order_management() -> SystemModel:
    return SystemModel(
        system_name="Order Management",
        requirements_ref=_requirements_ref("Order Management"),
        services=[ServiceSpec(id="svc-order", name="Order", domain_id="general")],
        capabilities=[BusinessCapability(id="cap-order", name="Order Processing")],
        domains=[DomainSpec(id="general", name="general")],
        data_models=[
            DataModelSpec(
                id="dm-order",
                name="order",
                owning_service_id="svc-order",
                fields=[
                    _id_field(),
                    FieldSpec(name="total", type=AbstractFieldType.DECIMAL, required=True),
                    FieldSpec(name="status", type=AbstractFieldType.TEXT, required=True),
                ],
            )
        ],
        security=SecurityModel(authentication=AuthenticationPosture.TOKEN_BASED),
    )


def inventory_tracker() -> SystemModel:
    return SystemModel(
        system_name="Inventory Tracker",
        requirements_ref=_requirements_ref("Inventory Tracker"),
        services=[ServiceSpec(id="svc-inventory", name="Inventory", domain_id="general")],
        capabilities=[BusinessCapability(id="cap-inventory", name="Inventory")],
        domains=[DomainSpec(id="general", name="general")],
        data_models=[
            DataModelSpec(
                id="dm-item",
                name="item",
                owning_service_id="svc-inventory",
                fields=[
                    _id_field(),
                    FieldSpec(name="name", type=AbstractFieldType.TEXT, required=True),
                    FieldSpec(name="quantity", type=AbstractFieldType.INTEGER, required=True),
                    FieldSpec(name="restock", type=AbstractFieldType.TIMESTAMP),
                ],
            )
        ],
        security=SecurityModel(authentication=AuthenticationPosture.TOKEN_BASED),
    )


def notification_hub() -> SystemModel:
    return SystemModel(
        system_name="Notification Hub",
        requirements_ref=_requirements_ref("Notification Hub"),
        services=[
            ServiceSpec(id="svc-notification", name="Notification", domain_id="general")
        ],
        capabilities=[BusinessCapability(id="cap-notification", name="Notification")],
        domains=[DomainSpec(id="general", name="general")],
        data_models=[
            DataModelSpec(
                id="dm-message",
                name="message",
                owning_service_id="svc-notification",
                fields=[
                    _id_field(),
                    FieldSpec(name="channel", type=AbstractFieldType.TEXT, required=True),
                    FieldSpec(name="delivered", type=AbstractFieldType.BOOLEAN, required=True),
                ],
            )
        ],
        # Public notification surface: no auth at the transport boundary.
        security=SecurityModel(authentication=AuthenticationPosture.ANONYMOUS),
    )


def payment_gateway() -> SystemModel:
    return SystemModel(
        system_name="Payment Gateway",
        requirements_ref=_requirements_ref("Payment Gateway"),
        services=[ServiceSpec(id="svc-payment", name="Payment", domain_id="general")],
        capabilities=[BusinessCapability(id="cap-payment", name="Payment")],
        domains=[DomainSpec(id="general", name="general")],
        data_models=[
            DataModelSpec(
                id="dm-transaction",
                name="transaction",
                owning_service_id="svc-payment",
                fields=[
                    _id_field(),
                    FieldSpec(name="amount", type=AbstractFieldType.DECIMAL, required=True),
                    FieldSpec(name="currency", type=AbstractFieldType.TEXT, required=True),
                ],
            )
        ],
        security=SecurityModel(
            authentication=AuthenticationPosture.TOKEN_BASED,
            data_classification=DataClassification.CONFIDENTIAL,
        ),
    )


DEFAULT_CORPUS: tuple[SystemModel, ...] = (
    order_management(),
    inventory_tracker(),
    notification_hub(),
    payment_gateway(),
)


def load_corpus(path: str | Path) -> list[SystemModel]:
    """Load a corpus from a JSON array (each element validated as a SystemModel)."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [SystemModel.model_validate(item) for item in data]


def dump_corpus(models: Iterable[SystemModel], path: str | Path) -> None:
    """Persist a corpus as a JSON array of validated SystemModel payloads."""
    data = [SystemModel.model_validate(m).model_dump(mode="json") for m in models]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def as_models(corpus: Iterable[SystemModel] | None = None) -> list[SystemModel]:
    return list(corpus if corpus is not None else DEFAULT_CORPUS)
