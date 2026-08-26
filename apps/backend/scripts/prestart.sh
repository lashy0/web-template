#!/usr/bin/env bash

set -euo pipefail

if [[ "${BACKEND_DEBUG:-false}" == "true" ]]; then
    echo "Debug mode enabled."
    set -x
fi

echo "Running database migrations..."
alembic upgrade head
echo "Database migrations completed."
echo "Bootstrapping the first administrator..."
python -m app.bootstrap
echo "First-administrator bootstrap completed."
