"""Corpus — workload definitions, categories, and novelty classification."""
from __future__ import annotations
from enum import Enum
from pydantic import BaseModel, ConfigDict


class Category(str, Enum):
    CRUD_SAAS = "crud_saas"
    ERP = "erp"
    BANKING = "banking"
    HEALTHCARE = "healthcare"
    LOGISTICS = "logistics"
    AI = "ai"
    GAMING = "gaming"
    IOT = "iot"
    ROBOTICS = "robotics"
    DISTRIBUTED = "distributed"
    EMBEDDED = "embedded"
    API = "api"
    STREAMING = "streaming"


ALL_CATEGORIES = list(Category)


class Workload(BaseModel):
    model_config = ConfigDict(frozen=True)
    intent: str
    category: Category
    seeds: list[str] = []


class NoveltyClass(str, Enum):
    TEMPLATE = "template"
    ARCHITECTURAL = "architectural"
    NOVEL_INTENT = "novel_intent"


def classify_novelty(w: Workload, seen_intents: set[str], seen_archs: set[str]) -> NoveltyClass:
    if w.intent not in seen_intents:
        return NoveltyClass.NOVEL_INTENT
    return NoveltyClass.ARCHITECTURAL


def default_corpus() -> list[Workload]:
    """Small seeded corpus for substrate validation (Campaign A)."""
    return [
        Workload(intent="crud-api-for-task-management", category=Category.CRUD_SAAS, seeds=["tasks"]),
        Workload(intent="inventory-management-service", category=Category.ERP, seeds=["inventory"]),
        Workload(intent="account-ledger-api", category=Category.BANKING, seeds=["accounts"]),
        Workload(intent="patient-registry-service", category=Category.HEALTHCARE, seeds=["patients"]),
        Workload(intent="shipment-tracker-api", category=Category.LOGISTICS, seeds=["shipments"]),
        Workload(intent="model-inference-endpoint", category=Category.AI, seeds=["models"]),
        Workload(intent="leaderboard-service", category=Category.GAMING, seeds=["scores"]),
        Workload(intent="device-telemetry-ingest", category=Category.IOT, seeds=["devices"]),
        Workload(intent="motion-planning-service", category=Category.ROBOTICS, seeds=["motions"]),
        Workload(intent="chat-message-relay", category=Category.DISTRIBUTED, seeds=["messages"]),
        Workload(intent="firmware-update-api", category=Category.EMBEDDED, seeds=["firmware"]),
        Workload(intent="petstore-openapi-service", category=Category.API, seeds=["pets"]),
        Workload(intent="event-stream-processor", category=Category.STREAMING, seeds=["events"]),
    ]
