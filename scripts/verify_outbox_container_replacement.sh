#!/usr/bin/env bash
set -euo pipefail

# Prove SQLite state survives removal/replacement of a container when the same
# host bind mount is retained. This deliberately does not start the full stack.
data_dir="$(mktemp -d)"
cleanup() {
  rm -rf "$data_dir"
}
trap cleanup EXIT

docker run --rm \
  -v "$data_dir:/data" \
  python:3.12-slim \
  python -c 'import sqlite3; c=sqlite3.connect("/data/maintenance-outbox.sqlite3"); c.execute("CREATE TABLE evidence (event_digest TEXT PRIMARY KEY, status TEXT NOT NULL)"); c.execute("INSERT INTO evidence VALUES (?, ?)", ("container-replacement-proof", "pending")); c.commit(); c.close()'

# The first container has exited and been removed. A new container mounts the
# exact same host directory and must read the previously committed row.
docker run --rm \
  -v "$data_dir:/data" \
  python:3.12-slim \
  python -c 'import sqlite3; c=sqlite3.connect("/data/maintenance-outbox.sqlite3"); row=c.execute("SELECT status FROM evidence WHERE event_digest=?", ("container-replacement-proof",)).fetchone(); assert row == ("pending",), row; print("PASS: SQLite row survived container replacement with host bind mount preserved")'
