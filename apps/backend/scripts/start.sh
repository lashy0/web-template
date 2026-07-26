#!/usr/bin/env bash

set -euo pipefail

if [[ "${BACKEND_DEBUG:-false}" == "true" ]]; then
    echo "Debug mode enabled."
    set -x
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

echo "Starting backend with ${BACKEND_WORKERS:-1} worker(s)..."

exec uvicorn app.main:create_app \
    --factory \
    --host 0.0.0.0 \
    --port 8000 \
    --workers ${BACKEND_WORKERS:-1} \
    --no-access-log
