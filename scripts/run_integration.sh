#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)/autonomous-api"
COMPOSE_FILE="tests/integration/docker-compose.yml"
docker compose -f "$COMPOSE_FILE" up -d --wait --wait-timeout 60
trap 'docker compose -f "$COMPOSE_FILE" down -v' EXIT
pytest -m integration -v
