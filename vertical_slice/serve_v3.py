"""VS-D27 deployment entrypoint: local uvicorn loopback for vs1-impl-obj001-v1.

Deployment glue only: builds the store + app from the frozen D25
implementation (vertical_slice/app_v3) and serves it on 127.0.0.1. Used
exclusively as a bounded observation fixture under explicit D27
authorization; not a production deployment. No import-time server start;
`python -m vertical_slice.serve_v3` runs uvicorn under __main__ only.

Environment:
  VS1_STORE_DIR  directory for the JSON-file store (tests set per-run temp).
  VS1_PORT       port to bind (default 8473). Port 0 requests an
                 OS-assigned port (runtime-instance identifier, never a
                 semantic input).
"""

from __future__ import annotations

import os

from vertical_slice.app_v3.api import create_app
from vertical_slice.app.security import production_token_generator
from vertical_slice.app.store import TaskTrackerStore

IMPLEMENTATION_ID = "vs1-impl-obj001-v1"
DEPLOYMENT_ID = "vs1-deploy-obj001-4ca3d24c13561599"

STORE_DIR = os.environ.get("VS1_STORE_DIR", os.path.join(os.getcwd(), ".vs1-store-v3"))
PORT = int(os.environ.get("VS1_PORT", "8473"))

store = TaskTrackerStore(STORE_DIR)
app = create_app(store, token_generator=production_token_generator())


def build_app(store_dir: str):
    """Factory for tests: v3 app bound to an explicit store directory."""
    from vertical_slice.app_v3.api import create_app as _create_app
    from vertical_slice.app.security import production_token_generator as _tokens
    from vertical_slice.app.store import TaskTrackerStore as _Store

    return _create_app(_Store(store_dir), token_generator=_tokens())


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="info")
