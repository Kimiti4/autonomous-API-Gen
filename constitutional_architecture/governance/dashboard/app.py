"""
Phase 28 — Governance Dashboard BFF (FastAPI).

A thin, auditable, API-driven console over the Governance Kernel
(spec §4/§5). Server-rendered Jinja2 templates; all mutations forward to
kernel APIs through GovernanceDashboardClient and are authorization-
checked at both the dashboard layer and the kernel layer.

Security posture:
  - every protected route requires an authenticated session
  - state-changing POSTs require a CSRF token
  - kernel failures render fail-closed (503), never silent allow
"""

from __future__ import annotations

import logging
import time
import uuid
from pathlib import Path
from typing import Dict

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from constitutional_architecture.governance.dashboard.auth import (
    Authenticator,
    CSRF_HEADER,
    SESSION_COOKIE,
    SessionManager,
    csrf_token_from_request,
    session_token_from_request,
)
from constitutional_architecture.governance.dashboard.client import (
    GovernanceDashboardClient,
)
from constitutional_architecture.governance.dashboard.config import DashboardConfig
from constitutional_architecture.governance.dashboard.errors import (
    DashboardError,
    ForbiddenError,
    KernelUnavailableError,
    NotFoundError,
    UnauthorizedError,
)
from constitutional_architecture.governance.dashboard.service import (
    DashboardAuthorizationError,
)

logger = logging.getLogger("governance.dashboard")

BASE_DIR = Path(__file__).resolve().parent


class Metrics:
    """Minimal observability counters (spec §12)."""

    def __init__(self) -> None:
        self.page_views: Dict[str, int] = {}
        self.api_errors = 0
        self.kernel_requests = 0
        self.approval_actions = 0
        self.exception_revocations = 0
        self.audit_verifications = 0
        self.kernel_request_duration_seconds = 0.0

    def page_view(self, route: str) -> None:
        self.page_views[route] = self.page_views.get(route, 0) + 1

    def record(self) -> Dict[str, float]:
        return {
            "dashboard_page_views_total": float(sum(self.page_views.values())),
            "dashboard_api_errors_total": float(self.api_errors),
            "dashboard_kernel_request_duration_seconds": self.kernel_request_duration_seconds,
            "dashboard_approval_actions_total": float(self.approval_actions),
            "dashboard_exception_revocations_total": float(self.exception_revocations),
            "dashboard_audit_verification_total": float(self.audit_verifications),
        }


def create_app(
    client: GovernanceDashboardClient,
    *,
    config: DashboardConfig | None = None,
    metrics: Metrics | None = None,
) -> FastAPI:
    config = config or DashboardConfig()
    metrics = metrics or Metrics()
    sessions = SessionManager(config)
    auth = Authenticator(config, sessions)
    templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
    app = FastAPI(title="Governance Console", docs_url=None, redoc_url=None)

    app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

    # ── context helpers ───────────────────────────────────────────────────
    def base_context(request: Request, user=None, **extra) -> dict:
        context = {
            "request": request,
            "app_name": config.app_name,
            "user": user,
            "csrf": (sessions.get_session(session_token_from_request(request)) or {}).get("csrf"),
        }
        context.update(extra)
        return context

    def current_user(request: Request):
        return auth.require_user(session_token_from_request(request))

    def require(user, permission: str) -> None:
        if not user.has_permission(permission, config):
            raise ForbiddenError(f"{permission} requires a privileged role.")

    def render(request: Request, template: str, user, **extra) -> HTMLResponse:
        metrics.page_view(request.url.path)
        return templates.TemplateResponse(
            request, template, base_context(request, user=user, **extra)
        )

    def mutation(request: Request, user, permission: str, csrf_form: str | None = None):
        """Auth + CSRF for state-changing actions; returns the kernel actor."""
        require(user, permission)
        session = sessions.get_session(session_token_from_request(request))
        if session is None:
            raise UnauthorizedError("Authentication required.")
        csrf = csrf_form or csrf_token_from_request(request)
        auth.require_csrf(session, csrf)
        return user.to_actor(config)

    # ── error handling (fail closed) ──────────────────────────────────────
    @app.exception_handler(DashboardError)
    async def dashboard_error_handler(request: Request, exc: DashboardError):
        metrics.api_errors += 1
        if exc.status_code >= 500 or isinstance(exc, KernelUnavailableError):
            logger.warning(
                "dashboard error",
                extra={"route": request.url.path, "error": type(exc).__name__, "detail": exc.message},
            )
        else:
            logger.info(
                "dashboard client error",
                extra={"route": request.url.path, "error": type(exc).__name__, "detail": exc.message},
            )
        status = exc.status_code
        if status == 503 or isinstance(exc, KernelUnavailableError):
            return templates.TemplateResponse(
                request,
                "errors/unavailable.html",
                base_context(request, message=exc.message, title=exc.title),
                status_code=503,
            )
        if isinstance(exc, (UnauthorizedError,)):
            return templates.TemplateResponse(
                request,
                "errors/unauthorized.html",
                base_context(request, message=exc.message, title=exc.title),
                status_code=401,
            )
        if isinstance(exc, (ForbiddenError,)):
            return templates.TemplateResponse(
                request,
                "errors/forbidden.html",
                base_context(request, message=exc.message, title=exc.title),
                status_code=403,
            )
        return templates.TemplateResponse(
            request,
            "errors/notfound.html",
            base_context(request, message=exc.message, title=exc.title),
            status_code=status,
        )

    @app.exception_handler(DashboardAuthorizationError)
    async def kernel_auth_error_handler(request: Request, exc: DashboardAuthorizationError):
        metrics.api_errors += 1
        return templates.TemplateResponse(
            request,
            "errors/forbidden.html",
            base_context(request, message=f"Kernel denied: {exc}", title="Kernel authorization denied"),
            status_code=403,
        )

    # ── health (no auth) ───────────────────────────────────────────────────
    @app.get("/health/live")
    def health_live():
        return JSONResponse({"status": "ok"})

    @app.get("/health/ready")
    def health_ready():
        ready = True
        reasons = []
        try:
            client.governance_health()
        except Exception as exc:
            ready = False
            reasons.append(f"kernel: {type(exc).__name__}")
        return JSONResponse(
            {"status": "ready" if ready else "not_ready", "checks": reasons or ["kernel", "auth", "templates", "static"]}
        )

    # ── auth routes ───────────────────────────────────────────────────────
    @app.get("/login")
    def login_page(request: Request):
        return templates.TemplateResponse(request, "login.html", base_context(request))

    @app.post("/login")
    def login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
        token, session = auth.login(username, password)
        response = RedirectResponse("/", status_code=303)
        response.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="lax")
        return response

    @app.post("/logout")
    def logout(request: Request):
        auth.logout(session_token_from_request(request))
        response = RedirectResponse("/login", status_code=303)
        response.delete_cookie(SESSION_COOKIE)
        return response

    # ── home / health summary (spec 7.1) ───────────────────────────────────
    @app.get("/", response_class=HTMLResponse)
    def home(request: Request):
        user = current_user(request)
        return render(request, "index.html", user, health=client.governance_health())

    # ── constitutions (spec 7.2) ───────────────────────────────────────────
    @app.get("/constitutions", response_class=HTMLResponse)
    def constitutions_list(request: Request):
        user = current_user(request)
        return render(request, "constitutions/list.html", user, constitutions=client.list_constitutions())

    @app.get("/constitutions/{constitution_id}", response_class=HTMLResponse)
    def constitution_detail(request: Request, constitution_id: str):
        user = current_user(request)
        return render(request, "constitutions/detail.html", user, constitution=client.get_constitution(constitution_id))

    # ── policy sets (spec 7.3) ─────────────────────────────────────────────
    @app.get("/policy-sets", response_class=HTMLResponse)
    def policy_sets_list(request: Request):
        user = current_user(request)
        return render(request, "policy_sets/list.html", user, policy_sets=client.list_policy_sets())

    @app.get("/policy-sets/{policy_set_id}", response_class=HTMLResponse)
    def policy_set_detail(request: Request, policy_set_id: str):
        user = current_user(request)
        return render(request, "policy_sets/detail.html", user, policy_set=client.get_policy_set(policy_set_id))

    # ── evaluations (spec 7.4/7.5) ─────────────────────────────────────────
    @app.get("/evaluations", response_class=HTMLResponse)
    def evaluations_list(request: Request, decision: str = "", action: str = "", subject_type: str = "", actor_id: str = ""):
        user = current_user(request)
        filters = {
            k: v
            for k, v in {
                "decision": decision or None,
                "action": action or None,
                "subject_type": subject_type or None,
                "actor_id": actor_id or None,
            }.items()
            if v
        }
        return render(
            request,
            "evaluations/list.html",
            user,
            evaluations=client.list_evaluations(filters),
            filters=filters,
        )

    @app.get("/evaluations/{decision_id}", response_class=HTMLResponse)
    def evaluation_detail(request: Request, decision_id: str):
        user = current_user(request)
        return render(request, "evaluations/detail.html", user, dossier=client.reconstruct_decision(decision_id))

    @app.get("/evaluations/{decision_id}/reconstruct", response_class=HTMLResponse)
    def reconstruction(request: Request, decision_id: str):
        user = current_user(request)
        return render(request, "evaluations/reconstruction.html", user, dossier=client.reconstruct_decision(decision_id))

    # ── approvals (spec 7.6) ───────────────────────────────────────────────
    @app.get("/approvals", response_class=HTMLResponse)
    def approvals_queue(request: Request, status: str = ""):
        user = current_user(request)
        filters = {"status": status or None}
        return render(
            request,
            "approvals/queue.html",
            user,
            approvals=client.list_approvals(filters),
            status_filter=status,
        )

    @app.get("/approvals/{approval_id}", response_class=HTMLResponse)
    def approval_detail(request: Request, approval_id: str):
        user = current_user(request)
        return render(request, "approvals/detail.html", user, approval=client.get_approval(approval_id))

    @app.post("/approvals/{approval_id}/approve")
    def approval_approve(request: Request, approval_id: str, comment: str = Form(""), csrf_token: str = Form("")):
        user = current_user(request)
        actor = mutation(request, user, "approve", csrf_token)
        metrics.approval_actions += 1
        result = client.submit_approval_decision(approval_id, actor, "APPROVED", comment)
        logger.info("approval action", extra={"approval_id": approval_id, "action": "APPROVED", "by": actor.actor_id})
        return RedirectResponse(f"/approvals/{approval_id}", status_code=303)

    @app.post("/approvals/{approval_id}/reject")
    def approval_reject(request: Request, approval_id: str, comment: str = Form(""), csrf_token: str = Form("")):
        user = current_user(request)
        actor = mutation(request, user, "reject", csrf_token)
        metrics.approval_actions += 1
        result = client.submit_approval_decision(approval_id, actor, "REJECTED", comment)
        logger.info("approval action", extra={"approval_id": approval_id, "action": "REJECTED", "by": actor.actor_id})
        return RedirectResponse(f"/approvals/{approval_id}", status_code=303)

    # ── exceptions (spec 7.7) ──────────────────────────────────────────────
    @app.get("/exceptions", response_class=HTMLResponse)
    def exceptions_list(request: Request, status: str = ""):
        user = current_user(request)
        filters = {"status": status or None}
        return render(
            request,
            "exceptions/list.html",
            user,
            exceptions=client.list_exceptions(filters),
            status_filter=status,
        )

    @app.get("/exceptions/{exception_id}", response_class=HTMLResponse)
    def exception_detail(request: Request, exception_id: str):
        user = current_user(request)
        return render(request, "exceptions/detail.html", user, exception=client.get_exception(exception_id))

    @app.post("/exceptions/{exception_id}/revoke")
    def exception_revoke(request: Request, exception_id: str, csrf_token: str = Form("")):
        user = current_user(request)
        actor = mutation(request, user, "revoke_exception", csrf_token)
        metrics.exception_revocations += 1
        result = client.revoke_exception(exception_id, actor)
        logger.info("exception revocation", extra={"exception_id": exception_id, "by": actor.actor_id})
        return RedirectResponse(f"/exceptions/{exception_id}", status_code=303)

    # ── audit (spec 7.8/7.9) ──────────────────────────────────────────────
    @app.get("/audit", response_class=HTMLResponse)
    def audit_list(request: Request, event_type: str = "", actor_id: str = "", subject_id: str = ""):
        user = current_user(request)
        filters = {
            k: v
            for k, v in {
                "event_type": event_type or None,
                "actor_id": actor_id or None,
                "subject_id": subject_id or None,
            }.items()
            if v
        }
        return render(request, "audit/list.html", user, events=client.list_audit_events(filters), filters=filters)

    @app.get("/audit/integrity", response_class=HTMLResponse)
    def audit_integrity(request: Request):
        user = current_user(request)
        return render(request, "audit/integrity.html", user, integrity=client.verify_audit_chain())

    @app.post("/audit/integrity/verify")
    def audit_integrity_verify(request: Request, csrf_token: str = Form("")):
        user = current_user(request)
        mutation(request, user, "verify_integrity", csrf_token)
        metrics.audit_verifications += 1
        return render(request, "audit/integrity.html", user, integrity=client.verify_audit_chain())

    @app.get("/audit/{event_id}", response_class=HTMLResponse)
    def audit_event_detail(request: Request, event_id: str):
        user = current_user(request)
        return render(request, "audit/event_detail.html", user, event=client.get_audit_event(event_id))

    # ── lineage (spec 7.10) ────────────────────────────────────────────────
    @app.get("/lineage", response_class=HTMLResponse)
    def lineage_explorer(request: Request):
        user = current_user(request)
        return render(request, "lineage/explorer.html", user, links=client.list_lineage())

    @app.get("/lineage/{artifact_id}", response_class=HTMLResponse)
    def lineage_artifact(request: Request, artifact_id: str):
        user = current_user(request)
        return render(request, "lineage/artifact_detail.html", user, trace=client.get_lineage_backward(artifact_id))

    @app.get("/lineage/{artifact_id}/backward", response_class=HTMLResponse)
    def lineage_backward(request: Request, artifact_id: str):
        user = current_user(request)
        return render(request, "lineage/artifact_detail.html", user, trace=client.get_lineage_backward(artifact_id))

    @app.get("/lineage/{artifact_id}/forward", response_class=HTMLResponse)
    def lineage_forward(request: Request, artifact_id: str):
        user = current_user(request)
        return render(request, "lineage/artifact_detail.html", user, trace=client.get_lineage_forward(artifact_id))

    # ── metrics (session-protected; observable via authenticated scrape) ─
    @app.get("/metrics")
    def metrics_endpoint(request: Request):
        current_user(request)
        return JSONResponse(metrics.record())

    return app


def demo_app() -> FastAPI:
    """App wired to a demo kernel (used by tests and local runs)."""
    from constitutional_architecture.governance.dashboard.render_console import (
        build_demo_kernel,
    )

    kernel = build_demo_kernel()
    client = GovernanceDashboardClient(kernel)
    return create_app(client)
