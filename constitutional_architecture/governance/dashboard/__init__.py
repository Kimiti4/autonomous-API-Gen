"""
Phase 28 — Governance Dashboard package.

Components:
  app.py         FastAPI BFF (routes, auth, CSRF, metrics, health)
  client.py      GovernanceDashboardClient (kernel contract, fail-closed)
  service.py     read views + kernel-only mutations (backend core)
  config.py      declarative users/roles/permissions
  auth.py        sessions, roles, CSRF
  view_models.py presentation dataclasses + redaction
  errors.py      dashboard error hierarchy
  console.html   static console artifact (render_console.py)
"""

from constitutional_architecture.governance.dashboard.app import create_app, demo_app
from constitutional_architecture.governance.dashboard.client import (
    GovernanceDashboardClient,
)
from constitutional_architecture.governance.dashboard.service import DashboardService

__all__ = ["create_app", "demo_app", "GovernanceDashboardClient", "DashboardService"]
