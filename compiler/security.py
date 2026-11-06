"""Authorization boundary for the standalone compiler API.

The API is intentionally unavailable for mutating/compiler operations until a
host application supplies an authorization callback that returns literal True.
"""
from __future__ import annotations

import inspect

from fastapi import HTTPException, Request


async def require_compiler_authorization(request: Request) -> bool:
    authorizer = getattr(request.app.state, "compiler_authorizer", None)
    if not callable(authorizer):
        raise HTTPException(
            status_code=503,
            detail="Compiler authorization is not configured; operation is blocked.",
        )
    try:
        decision = authorizer(request)
        if inspect.isawaitable(decision):
            decision = await decision
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Compiler authorization failed closed: {type(exc).__name__}.",
        ) from exc
    if decision is not True:
        raise HTTPException(
            status_code=403,
            detail="Compiler authorization did not explicitly approve this operation.",
        )
    return True
