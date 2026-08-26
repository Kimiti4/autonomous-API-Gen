"""Corpus — workload definitions, categories, novelty classification, and hash provenance."""
from __future__ import annotations
import hashlib
import json
from enum import Enum
from typing import Sequence
from pydantic import BaseModel, ConfigDict, Field


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
    seeds: Sequence[str] = Field(default_factory=list)


class NoveltyClass(str, Enum):
    TEMPLATE = "template"
    ARCHITECTURAL = "architectural"
    NOVEL_INTENT = "novel_intent"


def classify_novelty(w: Workload, seen_intents: set[str], seen_archs: set[str]) -> NoveltyClass:
    if w.intent not in seen_intents:
        return NoveltyClass.NOVEL_INTENT
    return NoveltyClass.ARCHITECTURAL


def _w(intent: str, cat: Category, seeds: list[str]) -> Workload:
    return Workload(intent=intent, category=cat, seeds=seeds)


_SEED_CORPUS: dict[Category, list[Workload]] = {
    Category.CRUD_SAAS: [
        _w("project management SaaS", Category.CRUD_SAAS, ["projects", "tasks", "teams"]),
        _w("customer relationship SaaS", Category.CRUD_SAAS, ["contacts", "deals", "pipeline"]),
        _w("inventory SaaS", Category.CRUD_SAAS, ["items", "stock", "warehouses"]),
    ],
    Category.ERP: [
        _w("procurement ERP", Category.ERP, ["purchase_orders", "suppliers", "invoices"]),
        _w("accounting ERP", Category.ERP, ["ledgers", "journals", "periods"]),
        _w("human resources ERP", Category.ERP, ["employees", "payroll", "leave"]),
    ],
    Category.BANKING: [
        _w("retail accounts platform", Category.BANKING, ["accounts", "transactions", "balances"]),
        _w("payments transfer platform", Category.BANKING, ["transfers", "ledgers", "confirmations"]),
        _w("lending platform", Category.BANKING, ["loans", "schedules", "repayments"]),
    ],
    Category.HEALTHCARE: [
        _w("clinical records platform", Category.HEALTHCARE, ["patients", "encounters", "observations"]),
        _w("care scheduling platform", Category.HEALTHCARE, ["appointments", "clinicians", "rooms"]),
        _w("clinical workflow platform", Category.HEALTHCARE, ["orders", "results", "tasks"]),
    ],
    Category.LOGISTICS: [
        _w("vehicle routing platform", Category.LOGISTICS, ["routes", "stops", "vehicles"]),
        _w("shipment tracking platform", Category.LOGISTICS, ["shipments", "events", "carriers"]),
        _w("freight management platform", Category.LOGISTICS, ["loads", "tenders", "invoices"]),
    ],
    Category.AI: [
        _w("model inference platform", Category.AI, ["models", "requests", "predictions"]),
        _w("model evaluation platform", Category.AI, ["datasets", "metrics", "runs"]),
        _w("training pipeline platform", Category.AI, ["training", "checkpoints", "deployments"]),
    ],
    Category.GAMING: [
        _w("multiplayer session platform", Category.GAMING, ["sessions", "players", "matches"]),
        _w("matchmaking platform", Category.GAMING, ["queues", "ratings", "lobbies"]),
        _w("player inventory platform", Category.GAMING, ["items", "grants", "trades"]),
    ],
    Category.IOT: [
        _w("device telemetry platform", Category.IOT, ["devices", "readings", "streams"]),
        _w("device management platform", Category.IOT, ["devices", "firmware", "commands"]),
        _w("sensor rules platform", Category.IOT, ["sensors", "thresholds", "alerts"]),
    ],
    Category.ROBOTICS: [
        _w("robot control platform", Category.ROBOTICS, ["robots", "commands", "telemetry"]),
        _w("mission planning platform", Category.ROBOTICS, ["missions", "waypoints", "constraints"]),
        _w("robot fleet platform", Category.ROBOTICS, ["robots", "tasks", "docks"]),
    ],
    Category.DISTRIBUTED: [
        _w("coordination service", Category.DISTRIBUTED, ["locks", "leaders", "elections"]),
        _w("replicated log service", Category.DISTRIBUTED, ["replicas", "logs", "snapshots"]),
        _w("distributed job service", Category.DISTRIBUTED, ["queues", "workers", "retries"]),
    ],
    Category.EMBEDDED: [
        _w("sensor acquisition firmware", Category.EMBEDDED, ["sensors", "samples", "buffers"]),
        _w("closed-loop controller", Category.EMBEDDED, ["inputs", "controllers", "actuators"]),
        _w("power management firmware", Category.EMBEDDED, ["modes", "budgets", "events"]),
    ],
    Category.API: [
        _w("multi-domain API gateway", Category.API, ["clients", "routes", "quotas"]),
        _w("developer portal", Category.API, ["apps", "keys", "docs"]),
        _w("usage billing platform", Category.API, ["usage", "meters", "invoices"]),
    ],
    Category.STREAMING: [
        _w("event processing platform", Category.STREAMING, ["topics", "consumers", "windows"]),
        _w("stream analytics platform", Category.STREAMING, ["events", "aggregations", "dashboards"]),
        _w("change data capture platform", Category.STREAMING, ["sources", "sinks", "transforms"]),
    ],
}


def default_corpus() -> list[Workload]:
    out: list[Workload] = []
    for cat in Category:
        out += _SEED_CORPUS[cat]
    return out


def corpus_hash() -> str:
    body = json.dumps(
        [w.model_dump() for w in default_corpus()],
        sort_keys=True, separators=(",", ":"),
    )
    return hashlib.sha256(body.encode()).hexdigest()
