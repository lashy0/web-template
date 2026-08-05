#!/usr/bin/env bash

set -euo pipefail

if [[ "${BACKEND_DEBUG:-false}" == "true" ]]; then
    echo "Debug mode enabled."
    set -x
fi

workers="${BACKEND_WORKERS:-1}"

if [[ ! "$workers" =~ ^[1-9][0-9]*$ ]]; then
    echo "Error: BACKEND_WORKERS must be a positive integer, got '$workers'." >&2
    exit 1
fi

if [[ "${BACKEND_RELOAD:-false}" == "true" ]]; then
    echo "Starting backend with auto-reload..."

    exec uvicorn app.main:create_app \
        --factory \
        --host 0.0.0.0 \
        --port 8000 \
        --no-access-log \
        --reload
fi

echo "Starting backend with $workers worker(s)..."

exec uvicorn app.main:create_app \
    --factory \
    --host 0.0.0.0 \
    --port 8000 \
    --workers "$workers" \
    --no-access-log
