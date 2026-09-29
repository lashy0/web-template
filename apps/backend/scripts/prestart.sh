#!/usr/bin/env bash

set -euo pipefail

echo "Running database migrations..."
alembic upgrade head
echo "Database migrations completed."
