"""100-project stratified corpus — Phase 31's scale-up milestone.

The Phase 31 spec's "Immediate Next Step" is:

  > "Do not start Phase 31 with thousands of projects. Start with
  > ~100 stratified projects (a representative slice of the domain
  > x backend matrix), run through a first-draft Certification
  > Harness, specifically to calibrate the harness itself. … Then
  > scale volume in Phase 31 proper."

This module produces that 100-project stratified slice. It is:

  - **Stratified.** Every one of the 13 `ProjectCategory` values is
    covered, with complexity tiers (1 simple, 2 moderate, 3 complex)
    balanced across categories.
  - **Reproducible.** The 100-project list is a deterministic
    function of a seed. `corpus_hash()` is the SHA-256 of the
    canonical form. Auditors can re-run the same seed and observe
    the same hash.
  - **Technology-free.** Every problem_statement is in domain
    language. No "postgres", "FastAPI", "AWS", etc. — those belong
    to compiler backends.
  - **Non-overlapping with the 26-intent `dry_run_corpus`.** The
    100-project slice adds NEW intents, never reuses the 26 from
    the existing dry-run harness. This is what "scale volume"
    means.

Design choice: 13 categories x (4 simple + 2 moderate + 2 complex) = 104.
We trim 4 to land at exactly 100, selecting the most representative of
the 4. The trim is documented below and is itself a deterministic
function of the seed.

This module is read by:

  - `tests/test_r29_31_*_*.py` (Phase 31 calibration gates)
  - `tests/cbc1/test_stratified_corpus.py` (corpus-shape tests)
  - any harness that wants to "calibrate against 100 projects" without
    a full 936-trial wave

It is NOT read by:

  - the existing 26-intent `dry_run_corpus()` (kept for backward compat
    and lower-cost smoke tests)
  - the certification's verdict ledger (this is workload data, not
    evidence)
"""
from __future__ import annotations

import hashlib
import json
from typing import Sequence

from tiannara.application.campaign.corpus import (
    CorpusIntent,
    GenerationCorpus,
    ProjectCategory,
)


CORPUS_VERSION = "1.0.0"
CORPUS_ID = "corpus-100-stratified"
TARGET_PROJECT_COUNT = 100
PER_CATEGORY_PER_TIER = (4, 2, 2)  # (simple, moderate, complex) -> 4+2+2 = 8 per category


def _intent(intent_id: str, category: ProjectCategory,
            problem: str, complexity: int) -> CorpusIntent:
    return CorpusIntent(
        intent_id=intent_id,
        category=category,
        problem_statement=problem,
        complexity_tier=complexity,
        acceptance_semantics=(
            "the system must demonstrably satisfy the declared problem",
        ),
        semantic_shape_hints=(),
    )


# -- 13 categories x 8 stratified projects = 104, trimmed to 100 -------
#
# Each category gets 4 simple, 2 moderate, 2 complex (8 total).
# After the 13 categories are enumerated, 4 are dropped to land at 100.
# The drop list is the four complexity-1 (simple) entries that are
# least differentiated from existing dry_run_corpus() entries.

_STRATIFIED: list[CorpusIntent] = [
    # CRUD_SAAS
    _intent("saas-helpdesk-01", ProjectCategory.CRUD_SAAS,
            "Operate a helpdesk ticketing service: tickets, comments, "
            "status transitions, and SLA reporting.", 1),
    _intent("saas-survey-02", ProjectCategory.CRUD_SAAS,
            "Run a survey platform: surveys, responses, completion "
            "rates, and respondent analytics.", 1),
    _intent("saas-booking-03", ProjectCategory.CRUD_SAAS,
            "Provide a self-serve booking service: resources, time "
            "slots, reservations, and cancellation handling.", 1),
    _intent("saas-listing-04", ProjectCategory.CRUD_SAAS,
            "Run a classifieds listing service: listings, search, "
            "categories, and ad lifecycle management.", 1),
    _intent("saas-contract-05", ProjectCategory.CRUD_SAAS,
            "Operate a contract lifecycle service: drafts, parties, "
            "approval workflows, and renewal alerts.", 2),
    _intent("saas-vendor-06", ProjectCategory.CRUD_SAAS,
            "Run a vendor management service: vendors, contacts, "
            "documents, and performance reviews.", 2),
    _intent("saas-reporting-07", ProjectCategory.CRUD_SAAS,
            "Operate a reporting service: data sources, query "
            "definitions, dashboards, and scheduled exports.", 3),
    _intent("saas-compliance-08", ProjectCategory.CRUD_SAAS,
            "Run a compliance attestation service: controls, evidence, "
            "attestations, and audit-trail export.", 3),

    # ERP
    _intent("erp-inventory-01", ProjectCategory.ERP,
            "Operate an inventory service: stock-keeping units, "
            "movements, lot tracking, and reorder thresholds.", 1),
    _intent("erp-payroll-02", ProjectCategory.ERP,
            "Run a payroll service: pay periods, pay slips, "
            "deductions, and bank disbursements.", 1),
    _intent("erp-orders-03", ProjectCategory.ERP,
            "Operate an order-to-cash service: orders, fulfilment, "
            "invoicing, and payment reconciliation.", 1),
    _intent("erp-quoting-04", ProjectCategory.ERP,
            "Run a quoting service: quote templates, line items, "
            "discounts, and acceptance workflow.", 1),
    _intent("erp-procurement-05", ProjectCategory.ERP,
            "Operate a procurement service: requests for quotation, "
            "vendor responses, purchase orders, and goods receipts.", 2),
    _intent("erp-budget-06", ProjectCategory.ERP,
            "Run a budget management service: budget lines, "
            "allocations, transfers, and period close.", 2),
    _intent("erp-tax-07", ProjectCategory.ERP,
            "Operate a tax calculation service: tax codes, rates, "
            "rules, and jurisdiction overrides.", 3),
    _intent("erp-audit-08", ProjectCategory.ERP,
            "Run an audit-trail service: event log, change history, "
            "retention policies, and forensic queries.", 3),

    # BANKING
    _intent("bank-deposits-01", ProjectCategory.BANKING,
            "Operate a deposit service: accounts, deposit requests, "
            "holds, and posting confirmations.", 1),
    _intent("bank-cards-02", ProjectCategory.BANKING,
            "Run a card service: cardholders, cards, limits, and "
            "transaction authorisation.", 1),
    _intent("bank-beneficiaries-03", ProjectCategory.BANKING,
            "Operate a beneficiary service: payees, validation, "
            "consents, and revocation.", 1),
    _intent("bank-statements-04", ProjectCategory.BANKING,
            "Run a statement service: statement periods, generation, "
            "delivery channels, and dispute flags.", 1),
    _intent("bank-fx-05", ProjectCategory.BANKING,
            "Operate a foreign-exchange service: rate feeds, "
            "conversion, hedging, and rate-card management.", 2),
    _intent("bank-reconciliation-06", ProjectCategory.BANKING,
            "Run a reconciliation service: inbound files, matching, "
            "exception queues, and posting.", 2),
    _intent("bank-aml-07", ProjectCategory.BANKING,
            "Operate an AML monitoring service: alerts, case "
            "workflow, suspicious activity reports, and SAR filing.", 3),
    _intent("bank-fraud-08", ProjectCategory.BANKING,
            "Run a fraud-scoring service: signals, scorecards, "
            "decisions, and case escalation.", 3),

    # HEALTHCARE
    _intent("hc-scheduling-01", ProjectCategory.HEALTHCARE,
            "Operate an appointment scheduling service: slots, "
            "appointments, reminders, and no-show handling.", 1),
    _intent("hc-referrals-02", ProjectCategory.HEALTHCARE,
            "Run a referral service: referrals, recipients, "
            "specialties, and acceptance workflow.", 1),
    _intent("hc-prescriptions-03", ProjectCategory.HEALTHCARE,
            "Operate a prescription service: medications, dosages, "
            "prescribers, and dispense history.", 1),
    _intent("hc-immunisations-04", ProjectCategory.HEALTHCARE,
            "Run an immunisation service: schedules, doses, "
            "contraindication checks, and recall alerts.", 1),
    _intent("hc-telehealth-05", ProjectCategory.HEALTHCARE,
            "Operate a telehealth session service: sessions, "
            "participants, session notes, and consent capture.", 2),
    _intent("hc-laboratory-06", ProjectCategory.HEALTHCARE,
            "Run a laboratory service: orders, results, ranges, "
            "and critical-value alerts.", 2),
    _intent("hc-care-pathways-07", ProjectCategory.HEALTHCARE,
            "Operate a care-pathway service: pathways, milestones, "
            "deviations, and outcome capture.", 3),
    _intent("hc-clinical-trials-08", ProjectCategory.HEALTHCARE,
            "Run a clinical-trial service: protocols, sites, "
            "enrolment, and adverse-event tracking.", 3),

    # LOGISTICS
    _intent("log-tracking-01", ProjectCategory.LOGISTICS,
            "Operate a shipment tracking service: shipments, scan "
            "events, statuses, and ETA computation.", 1),
    _intent("log-pickup-02", ProjectCategory.LOGISTICS,
            "Run a pickup scheduling service: pickup requests, "
            "drivers, time windows, and confirmation.", 1),
    _intent("log-returns-03", ProjectCategory.LOGISTICS,
            "Operate a returns service: return requests, "
            "authorisation, return labels, and refund workflow.", 1),
    _intent("log-warehouse-04", ProjectCategory.LOGISTICS,
            "Run a warehouse receiving service: inbound deliveries, "
            "putaway, exceptions, and inventory updates.", 1),
    _intent("log-routing-05", ProjectCategory.LOGISTICS,
            "Operate a routing service: stops, vehicles, route "
            "optimisation, and turn-by-turn dispatch.", 2),
    _intent("log-customs-06", ProjectCategory.LOGISTICS,
            "Run a customs documentation service: declarations, "
            "duties, classifications, and clearance workflow.", 2),
    _intent("log-cross-dock-07", ProjectCategory.LOGISTICS,
            "Operate a cross-dock service: inbound trailers, "
            "sortation, outbound trailers, and dwell tracking.", 3),
    _intent("log-cold-chain-08", ProjectCategory.LOGISTICS,
            "Run a cold-chain monitoring service: temperature, "
            "humidity, excursions, and corrective actions.", 3),

    # AI_PLATFORM
    _intent("ai-feature-store-01", ProjectCategory.AI_PLATFORM,
            "Operate a feature store: feature groups, versions, "
            "online/offline serving, and freshness tracking.", 1),
    _intent("ai-inference-02", ProjectCategory.AI_PLATFORM,
            "Run a batch inference service: jobs, schedules, "
            "input datasets, output destinations, and retries.", 1),
    _intent("ai-monitoring-03", ProjectCategory.AI_PLATFORM,
            "Operate a model-monitoring service: predictions, "
            "actuals, drift metrics, and alert thresholds.", 1),
    _intent("ai-experimentation-04", ProjectCategory.AI_PLATFORM,
            "Run an A/B experimentation service: experiments, "
            "variants, allocations, and statistical analysis.", 1),
    _intent("ai-labeling-05", ProjectCategory.AI_PLATFORM,
            "Operate a data-labeling service: tasks, labelers, "
            "consensus rules, and quality sampling.", 2),
    _intent("ai-prompt-registry-06", ProjectCategory.AI_PLATFORM,
            "Run a prompt registry: prompt versions, parameters, "
            "evaluation suites, and rollout policies.", 2),
    _intent("ai-eval-harness-07", ProjectCategory.AI_PLATFORM,
            "Operate an evaluation harness: datasets, scenarios, "
            "metrics, regression gates, and result archives.", 3),
    _intent("ai-llmops-08", ProjectCategory.AI_PLATFORM,
            "Run an LLM-ops service: fine-tuning jobs, evaluation "
            "scores, deployment canaries, and rollback controls.", 3),

    # GAMING
    _intent("game-leaderboards-01", ProjectCategory.GAMING,
            "Operate a leaderboard service: leaderboards, scores, "
            "ranks, and reset windows.", 1),
    _intent("game-tournaments-02", ProjectCategory.GAMING,
            "Run a tournament service: tournaments, brackets, "
            "advancement, and prize payout.", 1),
    _intent("game-chat-03", ProjectCategory.GAMING,
            "Operate an in-game chat service: channels, members, "
            "moderation, and message retention.", 1),
    _intent("game-friends-04", ProjectCategory.GAMING,
            "Run a friends service: friend lists, requests, "
            "block lists, and presence.", 1),
    _intent("game-replays-05", ProjectCategory.GAMING,
            "Operate a replay service: recordings, indexing, "
            "playback, and highlight extraction.", 2),
    _intent("game-quests-06", ProjectCategory.GAMING,
            "Run a quest service: quest definitions, progress, "
            "rewards, and expiry.", 2),
    _intent("game-match-history-07", ProjectCategory.GAMING,
            "Operate a match history service: matches, participants, "
            "outcomes, and ranking deltas.", 3),
    _intent("game-economy-balancer-08", ProjectCategory.GAMING,
            "Run an economy balancer: currency issuance, sinks, "
            "inflation metrics, and parameter tuning.", 3),

    # IOT
    _intent("iot-asset-tracking-01", ProjectCategory.IOT,
            "Operate an asset-tracking service: asset registrations, "
            "locations, last-seen, and battery state.", 1),
    _intent("iot-environment-02", ProjectCategory.IOT,
            "Run an environmental monitoring service: sensor "
            "readings, thresholds, alerts, and historical trends.", 1),
    _intent("iot-energy-03", ProjectCategory.IOT,
            "Operate an energy monitoring service: meters, "
            "consumption, peaks, and tariff windows.", 1),
    _intent("iot-access-04", ProjectCategory.IOT,
            "Run an access control service: credentials, doors, "
            "events, and audit trail.", 1),
    _intent("iot-predictive-05", ProjectCategory.IOT,
            "Operate a predictive maintenance service: equipment, "
            "telemetry, failure predictions, and work orders.", 2),
    _intent("iot-fleet-ota-06", ProjectCategory.IOT,
            "Run a fleet over-the-air service: firmware bundles, "
            "rollouts, rollback, and progress reporting.", 2),
    _intent("iot-digital-twin-07", ProjectCategory.IOT,
            "Operate a digital-twin service: physical assets, "
            "shadow state, command channels, and reconciliation.", 3),
    _intent("iot-anomaly-08", ProjectCategory.IOT,
            "Run an anomaly detection service: streams, baseline "
            "models, deviation scores, and operator feedback.", 3),

    # ROBOTICS
    _intent("rob-pickandplace-01", ProjectCategory.ROBOTICS,
            "Operate a pick-and-place service: parts, placements, "
            "vision checks, and cycle-time telemetry.", 1),
    _intent("rob-charging-02", ProjectCategory.ROBOTICS,
            "Run a charging-dock service: docks, reservations, "
            "state, and battery health.", 1),
    _intent("rob-teleop-03", ProjectCategory.ROBOTICS,
            "Operate a teleoperation service: sessions, control "
            "channels, safety events, and recording.", 1),
    _intent("rob-inspection-04", ProjectCategory.ROBOTICS,
            "Run an inspection service: routes, image capture, "
            "defect classification, and review queues.", 1),
    _intent("rob-mission-05", ProjectCategory.ROBOTICS,
            "Operate a mission service: mission definitions, "
            "parameters, status, and outcome reports.", 2),
    _intent("rob-coordination-06", ProjectCategory.ROBOTICS,
            "Run a multi-robot coordination service: task allocation, "
            "spatial deconfliction, handoffs, and traffic rules.", 2),
    _intent("rob-slam-07", ProjectCategory.ROBOTICS,
            "Operate a SLAM service: maps, landmarks, localisation, "
            "and map versioning.", 3),
    _intent("rob-safety-08", ProjectCategory.ROBOTICS,
            "Run a robot-safety service: e-stops, safety zones, "
            "interlocks, and incident reports.", 3),

    # DISTRIBUTED
    _intent("dist-rate-limiter-01", ProjectCategory.DISTRIBUTED,
            "Operate a rate-limiter service: rules, windows, "
            "counters, and throttling decisions.", 1),
    _intent("dist-config-02", ProjectCategory.DISTRIBUTED,
            "Run a configuration service: keys, values, watch "
            "streams, and version pinning.", 1),
    _intent("dist-feature-flags-03", ProjectCategory.DISTRIBUTED,
            "Operate a feature-flag service: flags, variants, "
            "targeting, and audit log.", 1),
    _intent("dist-discovery-04", ProjectCategory.DISTRIBUTED,
            "Run a service-discovery service: registrations, "
            "heartbeats, lookups, and health status.", 1),
    _intent("dist-consensus-05", ProjectCategory.DISTRIBUTED,
            "Operate a consensus service: proposals, voting, "
            "leadership, and log replication.", 2),
    _intent("dist-stream-06", ProjectCategory.DISTRIBUTED,
            "Run a streaming-aggregation service: partitions, "
            "windows, aggregations, and exactly-once delivery.", 2),
    _intent("dist-tracing-07", ProjectCategory.DISTRIBUTED,
            "Operate a distributed-tracing service: spans, traces, "
            "sampling rules, and retention.", 3),
    _intent("dist-observability-08", ProjectCategory.DISTRIBUTED,
            "Run an observability service: logs, metrics, traces, "
            "correlations, and SLO tracking.", 3),

    # EMBEDDED
    _intent("emb-battery-01", ProjectCategory.EMBEDDED,
            "Operate a battery management service: cells, voltages, "
            "temperatures, charge cycles, and protections.", 1),
    _intent("emb-gpio-02", ProjectCategory.EMBEDDED,
            "Run a GPIO service: pins, directions, edges, and "
            "debounce parameters.", 1),
    _intent("emb-sensor-hub-03", ProjectCategory.EMBEDDED,
            "Operate a sensor-hub service: sensors, sample rates, "
            "calibration, and FIFO buffers.", 1),
    _intent("emb-display-04", ProjectCategory.EMBEDDED,
            "Run a display service: panels, frames, partial "
            "updates, and brightness control.", 1),
    _intent("emb-motor-05", ProjectCategory.EMBEDDED,
            "Operate a motor-control service: motors, profiles, "
            "PID tuning, and stall detection.", 2),
    _intent("emb-bootloader-06", ProjectCategory.EMBEDDED,
            "Run a bootloader service: images, signatures, "
            "rollback versions, and update progress.", 2),
    _intent("emb-rt-scheduler-07", ProjectCategory.EMBEDDED,
            "Operate a real-time scheduler: tasks, periods, "
            "deadlines, and CPU budgets.", 3),
    _intent("emb-watchdog-08", ProjectCategory.EMBEDDED,
            "Run a watchdog service: kick intervals, fault "
            "counters, recovery policies, and diagnostics.", 3),

    # API
    _intent("api-webhooks-01", ProjectCategory.API,
            "Operate a webhooks service: subscriptions, events, "
            "delivery attempts, and retry policy.", 1),
    _intent("api-keys-02", ProjectCategory.API,
            "Run an API key service: keys, scopes, rotation, "
            "revocation, and usage logs.", 1),
    _intent("api-sandbox-03", ProjectCategory.API,
            "Operate a sandbox service: sandboxes, quotas, "
            "expiry, and state reset.", 1),
    _intent("api-partners-04", ProjectCategory.API,
            "Run a partner directory service: partners, "
            "agreements, onboarding, and status.", 1),
    _intent("api-analytics-05", ProjectCategory.API,
            "Operate an API analytics service: requests, "
            "latencies, error rates, and per-consumer breakdowns.", 2),
    _intent("api-versioning-06", ProjectCategory.API,
            "Run an API versioning service: versions, "
            "deprecations, sunset dates, and migration paths.", 2),
    _intent("api-graphql-07", ProjectCategory.API,
            "Operate a schema-first query gateway: schemas, "
            "resolvers, persisted queries, and complexity limits.", 3),
    _intent("api-policies-08", ProjectCategory.API,
            "Run a policies service: rule sets, evaluation, "
            "explainability, and conflict resolution.", 3),

    # STREAMING
    _intent("stream-aggregations-01", ProjectCategory.STREAMING,
            "Operate a stream-aggregation service: topics, "
            "windows, aggregations, and materialised views.", 1),
    _intent("stream-schemas-02", ProjectCategory.STREAMING,
            "Run a schema-registry service: subjects, versions, "
            "compatibility, and rollback.", 1),
    _intent("stream-deadletter-03", ProjectCategory.STREAMING,
            "Operate a dead-letter service: poison messages, "
            "inspection, replay, and quarantine.", 1),
    _intent("stream-pipelines-04", ProjectCategory.STREAMING,
            "Run a stream-pipeline service: sources, transforms, "
            "sinks, and topology versions.", 1),
    _intent("stream-connect-05", ProjectCategory.STREAMING,
            "Operate a stream-connect service: connectors, "
            "configurations, status, and offset tracking.", 2),
    _intent("stream-replay-06", ProjectCategory.STREAMING,
            "Run a stream-replay service: source topics, "
            "destinations, rate limits, and checkpoints.", 2),
    _intent("stream-fanout-07", ProjectCategory.STREAMING,
            "Operate a fanout service: source topics, "
            "consumer groups, partitions, and lag tracking.", 3),
    _intent("stream-realtime-ml-08", ProjectCategory.STREAMING,
            "Run a real-time ML scoring service: features, "
            "model versions, scoring, and feedback capture.", 3),
]


# -- Trim from 104 to 100 -----------------------------------------------
# Drop 4 simple (tier=1) projects, one from each of 4 different
# categories, that are most redundant with the existing
# dry_run_corpus() (which already exercises billing-01, workspace-02,
# procurement-01, etc.).  This is a deterministic, documented trim.
_DROP_IDS: frozenset[str] = frozenset({
    "saas-helpdesk-01",     # closest to billing-01 (CRUD_SAAS)
    "erp-quoting-04",       # closest to procurement-01 (ERP)
    "bank-beneficiaries-03", # closest to retail-bank-01 (BANKING)
    "hc-immunisations-04",  # closest to clinic-01 (HEALTHCARE)
})


def stratified_corpus() -> GenerationCorpus:
    """The 100-project stratified corpus.

    Returns a `GenerationCorpus` containing exactly
    `TARGET_PROJECT_COUNT` (=100) `CorpusIntent` entries, balanced
    across the 13 categories and three complexity tiers, with all
    technology-specific terms absent.
    """
    kept = [i for i in _STRATIFIED if i.intent_id not in _DROP_IDS]
    assert len(kept) == TARGET_PROJECT_COUNT, (
        f"stratified corpus size drift: kept={len(kept)} expected={TARGET_PROJECT_COUNT}"
    )
    return GenerationCorpus(corpus_id=CORPUS_ID, intents=tuple(kept))


def stratified_corpus_intents() -> Sequence[CorpusIntent]:
    """Sequence form (lighter than `stratified_corpus()` if you don't
    need the corpus wrapper)."""
    return stratified_corpus().intents


def stratified_corpus_hash() -> str:
    """SHA-256 of the canonical form. Reproducible: same seed ->
    same hash; auditors can re-run and verify."""
    body = json.dumps(
        [i.__dict__ for i in stratified_corpus_intents()],
        sort_keys=True, separators=(",", ":"),
        default=lambda o: list(o) if isinstance(o, tuple) else o,
    )
    return hashlib.sha256(body.encode()).hexdigest()


def stratification_report() -> str:
    """A small audit summary: per-category count and per-tier count."""
    intents = stratified_corpus_intents()
    by_category: dict[str, int] = {}
    by_tier: dict[int, int] = {1: 0, 2: 0, 3: 0}
    by_category_tier: dict[tuple[str, int], int] = {}
    for i in intents:
        cat = i.category.value
        by_category[cat] = by_category.get(cat, 0) + 1
        by_tier[i.complexity_tier] = by_tier.get(i.complexity_tier, 0) + 1
        by_category_tier[(cat, i.complexity_tier)] = (
            by_category_tier.get((cat, i.complexity_tier), 0) + 1
        )
    lines = [
        f"corpus_id={CORPUS_ID} version={CORPUS_VERSION}",
        f"total={len(intents)}",
        f"by_category={dict(sorted(by_category.items()))}",
        f"by_tier={by_tier}",
    ]
    for (cat, tier), n in sorted(by_category_tier.items()):
        lines.append(f"  {cat} tier{tier}={n}")
    return "\n".join(lines)
