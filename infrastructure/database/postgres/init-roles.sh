#!/usr/bin/env bash

set -euo pipefail

: "${POSTGRES_MIGRATOR_PASSWORD:?POSTGRES_MIGRATOR_PASSWORD is required}"
: "${POSTGRES_RUNTIME_PASSWORD:?POSTGRES_RUNTIME_PASSWORD is required}"

SQL_FILE="/usr/local/share/web-database/init-roles.sql"

psql \
    --username="${POSTGRES_USER}" \
    --dbname="${POSTGRES_DB}" \
    --set=ON_ERROR_STOP=1 \
    --set=migrator_password="${POSTGRES_MIGRATOR_PASSWORD}" \
    --set=runtime_password="${POSTGRES_RUNTIME_PASSWORD}" \
    --single-transaction \
    --file="${SQL_FILE}"
