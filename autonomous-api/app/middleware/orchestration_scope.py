"""Response headers marking orchestration ingress scope (Checkpoint 056)."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class OrchestrationScopeMiddleware(BaseHTTPMiddleware):
    """Annotates HTTP responses so clients cannot confuse subordinate compile with governed lifecycle."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        path = request.url.path
        if path.startswith("/api/v1/orchestration/full-stack"):
            response.headers["X-ESAP-Orchestration-Scope"] = "canonical-full-stack"
        elif "/evolve/" in path or path.endswith("/evolve/sync"):
            response.headers["X-ESAP-Orchestration-Scope"] = "subordinate-evolution"
        elif path.startswith("/api/v1/publication/"):
            response.headers["X-ESAP-Orchestration-Scope"] = "governance-publication"
        return response
