"""VS-D16 deployment entrypoint: local uvicorn loopback for vs1-impl-v2.

Deployment glue only (per D16 §§7/22/23): builds the store + app from the
frozen D15 implementation (vertical_slice/app_v2) and serves it on
127.0.0.1. No import-time server start; `python -m vertical_slice.serve_v2`
runs uvicorn under __main__ only. No observation, interpretation, or
evolution work is performed here.

Environment:
  VS1_STORE_DIR  directory for the JSON-file store (required in production
                 use; tests set a per-run temp dir).
  VS1_PORT       port to bind (default 8472). Port 0 requests an
                 OS-assigned port; the bound port is a runtime-instance
                 identifier recorded in deployment evidence, never a
                 semantic input.
"""

from __future__ import annotations

import os

from vertical_slice.app_v2.api import create_app
from vertical_slice.app.security import production_token_generator
from vertical_slice.app.store import TaskTrackerStore

IMPLEMENTATION_ID = "vs1-impl-v2"

STORE_DIR = os.environ.get("VS1_STORE_DIR", os.path.join(os.getcwd(), ".vs1-store-v2"))
PORT = int(os.environ.get("VS1_PORT", "8472"))

store = TaskTrackerStore(STORE_DIR)
app = create_app(store, token_generator=production_token_generator())


def build_app(store_dir: str):
    """Factory for tests: v2 app bound to an explicit store directory."""
    from vertical_slice.app_v2.api import create_app as _create_app
    from vertical_slice.app.security import production_token_generator as _tokens
    from vertical_slice.app.store import TaskTrackerStore as _Store

    return _create_app(_Store(store_dir), token_generator=_tokens())


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="info")
