#!/usr/bin/env bash

set -euo pipefail

if [[ "${BACKEND_DEBUG:-false}" == "true" ]]; then
    set -x
fi

exec uvicorn app.realtime.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --no-access-log
