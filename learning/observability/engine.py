"""
Learning observability engine.
"""

from __future__ import annotations

import html
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from ..utils import deterministic_id, utcnow
from .models import (
    DashboardPanel,
    LearningMetricsSnapshot,
    ObservabilityPolicy,
    OperationalDashboard,
    OperationalHealth,
    OperationalStatus,
)


def parse_timestamp(value: Any) -> Optional[datetime]:
    """Parse ISO timestamp safely."""

    if not isinstance(value, str):
        return None

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed


class LearningObservabilityEngine:
    """Provides observability over the learning infrastructure."""

    def __init__(
        self,
        learning_engine=None,
        analytics_engine=None,
        integration_engine=None,
        governance_engine=None,
        knowledge_sync_engine=None,
        policy: ObservabilityPolicy | None = None,
    ) -> None:
        self.learning_engine = learning_engine
        self.analytics_engine = analytics_engine
        self.integration_engine = integration_engine
        self.governance_engine = governance_engine
        self.knowledge_sync_engine = knowledge_sync_engine

        self.policy = policy or ObservabilityPolicy()

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def metrics_snapshot(self) -> LearningMetricsSnapshot:
        signal_count = self._signal_count()
        recent_signal_count = self._recent_signal_count()

        anomaly_count = self._count_items(self.analytics_engine, "anomalies")
        cluster_count = self._count_items(self.analytics_engine, "clusters")
        insight_count = self._count_items(self.analytics_engine, "insights")

        insight_backlog = self._insight_backlog()

        submission_count = self._submission_count()
        pending_approval_count = self._pending_approval_count()

        kill_switch_enabled = self._kill_switch_enabled()
        safety_blocker_count = self._safety_blocker_count(kill_switch_enabled)

        average_cluster_confidence = self._average_attribute(
            self.analytics_engine,
            "clusters",
            "confidence",
        )

        average_insight_confidence = self._average_attribute(
            self.analytics_engine,
            "insights",
            "confidence",
        )

        quality_score = self._quality_score()

        knowledge_sync_counts = self._knowledge_sync_counts()

        return LearningMetricsSnapshot(
            signal_count=signal_count,
            recent_signal_count=recent_signal_count,
            anomaly_count=anomaly_count,
            cluster_count=cluster_count,
            insight_count=insight_count,
            insight_backlog=insight_backlog,
            submission_count=submission_count,
            pending_approval_count=pending_approval_count,
            kill_switch_enabled=kill_switch_enabled,
            safety_blocker_count=safety_blocker_count,
            average_cluster_confidence=average_cluster_confidence,
            average_insight_confidence=average_insight_confidence,
            quality_score=quality_score,
            knowledge_sync_counts=knowledge_sync_counts,
        )

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    def operational_health(self) -> OperationalHealth:
        snapshot = self.metrics_snapshot()

        reasons: List[str] = []

        anomaly_rate = 0.0

        if snapshot.signal_count > 0:
            anomaly_rate = snapshot.anomaly_count / snapshot.signal_count

        checks: Dict[str, bool] = {
            "learning_engine_present": self.learning_engine is not None,
            "analytics_engine_present": self.analytics_engine is not None,
            "kill_switch_disabled": not snapshot.kill_switch_enabled,
            "no_safety_blockers": snapshot.safety_blocker_count == 0,
            "anomaly_rate_ok": (
                anomaly_rate
                <= self.policy.anomaly_rate_warning_threshold
            ),
            "approval_backlog_ok": (
                snapshot.pending_approval_count
                <= self.policy.pending_approvals_warning_threshold
            ),
            "recent_signals_present": snapshot.recent_signal_count > 0,
        }

        status = OperationalStatus.HEALTHY

        if snapshot.kill_switch_enabled:
            status = OperationalStatus.DEGRADED
            reasons.append("Learning kill switch is active.")

        if snapshot.safety_blocker_count >= (
            self.policy.safety_blocker_critical_threshold
        ):
            status = OperationalStatus.DEGRADED
            reasons.append("Safety blockers are present.")

        if anomaly_rate >= self.policy.anomaly_rate_critical_threshold:
            status = OperationalStatus.CRITICAL
            reasons.append("Anomaly rate is critically high.")
        elif anomaly_rate >= self.policy.anomaly_rate_warning_threshold:
            if status == OperationalStatus.HEALTHY:
                status = OperationalStatus.WARNING

            reasons.append("Anomaly rate is above warning threshold.")

        if snapshot.pending_approval_count > (
            self.policy.pending_approvals_warning_threshold
        ):
            if status == OperationalStatus.HEALTHY:
                status = OperationalStatus.WARNING

            reasons.append("Approval backlog is above warning threshold.")

        if not self.learning_engine or not self.analytics_engine:
            if status == OperationalStatus.HEALTHY:
                status = OperationalStatus.WARNING

            reasons.append("One or more learning engines are not configured.")

        if snapshot.signal_count > 0 and snapshot.recent_signal_count == 0:
            if status == OperationalStatus.HEALTHY:
                status = OperationalStatus.WARNING

            reasons.append("No recent signals received.")

        return OperationalHealth(
            status=status,
            reasons=reasons,
            checks=checks,
        )

    # ------------------------------------------------------------------
    # Dashboard
    # ------------------------------------------------------------------

    def dashboard(self) -> OperationalDashboard:
        snapshot = self.metrics_snapshot()
        health = self.operational_health()

        anomaly_rate = 0.0

        if snapshot.signal_count > 0:
            anomaly_rate = snapshot.anomaly_count / snapshot.signal_count

        panels: List[DashboardPanel] = []

        panels.append(
            DashboardPanel(
                title="Learning Pipeline",
                panel_type="metric_table",
                data={
                    "signal_count": snapshot.signal_count,
                    "recent_signal_count": snapshot.recent_signal_count,
                    "anomaly_count": snapshot.anomaly_count,
                    "anomaly_rate": round(anomaly_rate, 4),
                },
            )
        )

        panels.append(
            DashboardPanel(
                title="Anomaly Correlation",
                panel_type="metric_table",
                data={
                    "cluster_count": snapshot.cluster_count,
                    "average_cluster_confidence": (
                        snapshot.average_cluster_confidence
                    ),
                },
            )
        )

        panels.append(
            DashboardPanel(
                title="Learning Insights",
                panel_type="metric_table",
                data={
                    "insight_count": snapshot.insight_count,
                    "insight_backlog": snapshot.insight_backlog,
                    "average_insight_confidence": (
                        snapshot.average_insight_confidence
                    ),
                },
            )
        )

        panels.append(
            DashboardPanel(
                title="Governance",
                panel_type="metric_table",
                data={
                    "kill_switch_enabled": snapshot.kill_switch_enabled,
                    "pending_approval_count": (
                        snapshot.pending_approval_count
                    ),
                    "safety_blocker_count": snapshot.safety_blocker_count,
                },
            )
        )

        panels.append(
            DashboardPanel(
                title="Evolution Feedback",
                panel_type="metric_table",
                data={
                    "submission_count": snapshot.submission_count,
                    "last_bundle_id": self._last_bundle_id(),
                },
            )
        )

        panels.append(
            DashboardPanel(
                title="Knowledge Graph Sync",
                panel_type="metric_table",
                data=snapshot.knowledge_sync_counts,
            )
        )

        dashboard_id = deterministic_id(
            "learning_operational_dashboard",
            {
                "generated_at": snapshot.generated_at,
                "status": health.status.value,
            },
        )

        return OperationalDashboard(
            id=dashboard_id,
            title="Continuous Learning Operational Dashboard",
            status=health.status,
            reasons=health.reasons,
            panels=panels,
            generated_at=snapshot.generated_at,
        )

    def render_dashboard_html(
        self,
        dashboard: OperationalDashboard,
    ) -> str:
        rows: List[str] = []

        rows.append("<html>")
        rows.append("<head>")
        rows.append(f"<title>{html.escape(dashboard.title)}</title>")
        rows.append(
            "<style>"
            "body { font-family: monospace; margin: 24px; }"
            "table { border-collapse: collapse; margin-bottom: 24px; }"
            "th, td { border: 1px solid #444; padding: 6px 10px; }"
            "th { background: #222; color: #fff; }"
            "</style>"
        )
        rows.append("</head>")
        rows.append("<body>")

        rows.append(f"<h1>{html.escape(dashboard.title)}</h1>")
        rows.append(f"<p>Status: {html.escape(dashboard.status.value)}</p>")

        if dashboard.reasons:
            rows.append("<ul>")
            for reason in dashboard.reasons:
                rows.append(f"<li>{html.escape(reason)}</li>")
            rows.append("</ul>")

        for panel in dashboard.panels:
            rows.append(f"<h2>{html.escape(panel.title)}</h2>")
            rows.append("<table>")
            rows.append("<tr><th>Metric</th><th>Value</th></tr>")

            for key, value in panel.data.items():
                rows.append(
                    "<tr>"
                    f"<td>{html.escape(str(key))}</td>"
                    f"<td>{html.escape(str(value))}</td>"
                    "</tr>"
                )

            rows.append("</table>")

        rows.append("</body>")
        rows.append("</html>")

        return "\n".join(rows)

    # ------------------------------------------------------------------
    # Report
    # ------------------------------------------------------------------

    def report(self) -> Dict[str, Any]:
        snapshot = self.metrics_snapshot()
        health = self.operational_health()

        return {
            "metrics": snapshot.model_dump(),
            "health": health.model_dump(),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _signal_count(self) -> int:
        pipeline = getattr(self.learning_engine, "pipeline", None)

        if not pipeline:
            return 0

        signals = getattr(pipeline, "signals", [])

        return len(signals)

    def _recent_signal_count(self) -> int:
        pipeline = getattr(self.learning_engine, "pipeline", None)

        if not pipeline:
            return 0

        signals = getattr(pipeline, "signals", [])

        now = utcnow()

        window = timedelta(
            minutes=self.policy.recent_signal_window_minutes
        )

        count = 0

        for signal in signals:
            timestamp = parse_timestamp(getattr(signal, "timestamp", None))

            if timestamp and now - timestamp <= window:
                count += 1

        return count

    def _count_items(self, engine: Any, attribute: str) -> int:
        items = getattr(engine, attribute, None)

        if not items:
            return 0

        return len(items)

    def _average_attribute(
        self,
        engine: Any,
        attribute: str,
        value_attribute: str,
    ) -> Optional[float]:
        items = getattr(engine, attribute, None)

        if not items:
            return None

        values: List[float] = []

        iterable = items.values() if isinstance(items, dict) else items

        for item in iterable:
            value = getattr(item, value_attribute, None)

            if value is None:
                continue

            try:
                values.append(float(value))
            except Exception:
                continue

        if not values:
            return None

        return round(sum(values) / len(values), 4)

    def _insight_backlog(self) -> int:
        insights = getattr(self.analytics_engine, "insights", None)

        if not insights:
            return 0

        processed_insight_ids = getattr(
            self.integration_engine,
            "processed_insight_ids",
            set(),
        )

        if processed_insight_ids is None:
            processed_insight_ids = set()

        iterable = insights.values() if isinstance(insights, dict) else insights

        backlog = 0

        for insight in iterable:
            insight_id = getattr(insight, "id", None)

            if insight_id and insight_id not in processed_insight_ids:
                backlog += 1

        return backlog

    def _submission_count(self) -> int:
        submissions = getattr(self.integration_engine, "submissions", None)

        if not submissions:
            return 0

        return len(submissions)

    def _pending_approval_count(self) -> int:
        approvals = getattr(self.governance_engine, "approvals", None)

        if not approvals:
            return 0

        iterable = approvals.values() if isinstance(approvals, dict) else approvals

        count = 0

        for approval in iterable:
            status = getattr(approval, "status", None)

            if status == "PENDING":
                count += 1

        return count

    def _kill_switch_enabled(self) -> bool:
        kill_switch = getattr(self.governance_engine, "kill_switch", None)

        if not kill_switch:
            return False

        return bool(getattr(kill_switch, "enabled", False))

    def _safety_blocker_count(self, kill_switch_enabled: bool) -> int:
        count = 0

        if kill_switch_enabled:
            count += 1

        explicit_blockers = getattr(
            self.governance_engine,
            "safety_blocker_count",
            0,
        )

        try:
            count += int(explicit_blockers)
        except Exception:
            pass

        return count

    def _quality_score(self) -> Optional[float]:
        quality_score = getattr(
            self.governance_engine,
            "last_quality_score",
            None,
        )

        if quality_score is None:
            return None

        try:
            return float(quality_score)
        except Exception:
            return None

    def _knowledge_sync_counts(self) -> Dict[str, int]:
        registry = getattr(self.knowledge_sync_engine, "registry", None)

        if not registry:
            return {}

        return {
            "synced_signals": len(
                getattr(registry, "synced_signal_ids", set())
            ),
            "synced_anomalies": len(
                getattr(registry, "synced_anomaly_ids", set())
            ),
            "synced_clusters": len(
                getattr(registry, "synced_cluster_ids", set())
            ),
            "synced_insights": len(
                getattr(registry, "synced_insight_ids", set())
            ),
            "synced_objectives": len(
                getattr(registry, "synced_objectives", set())
            ),
        }

    def _last_bundle_id(self) -> Optional[str]:
        return getattr(self.integration_engine, "last_bundle_id", None)
