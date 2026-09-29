#!/usr/bin/env bash

set -euo pipefail

workers="${BACKEND_WORKERS:-1}"

if [[ ! "$workers" =~ ^[1-9][0-9]*$ ]]; then
    echo "Error: BACKEND_WORKERS must be a positive integer, got '$workers'." >&2
    exit 1
fi

# Only Traefik reaches the API, so its X-Forwarded-For carries the client address.
server=(
    uvicorn app.server.asgi:create_app
    --factory
    --host 0.0.0.0
    --port 8000
    --no-access-log
    --proxy-headers
    --forwarded-allow-ips "*"
)

if [[ "${BACKEND_RELOAD:-false}" == "true" ]]; then
    echo "Starting API with auto-reload..."
    exec "${server[@]}" --reload
fi

echo "Starting API with $workers worker(s)..."
exec "${server[@]}" --workers "$workers"
