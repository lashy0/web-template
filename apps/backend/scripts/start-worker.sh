#!/usr/bin/env bash

set -euo pipefail

if [[ "${BACKEND_DEBUG:-false}" == "true" ]]; then
    set -x
fi

exec celery \
    --app app.worker.celery_app:celery_app \
    worker \
    --without-gossip \
    --without-mingle \
    --without-heartbeat \
    --loglevel "${WORKER_LOG_LEVEL:-INFO}"
