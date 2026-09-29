#!/usr/bin/env bash

set -euo pipefail

: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${BACKEND_POSTGRES_MIGRATOR_PASSWORD:?BACKEND_POSTGRES_MIGRATOR_PASSWORD is required}"
: "${BACKEND_POSTGRES_RUNTIME_PASSWORD:?BACKEND_POSTGRES_RUNTIME_PASSWORD is required}"
: "${KRATOS_POSTGRES_MIGRATOR_PASSWORD:?KRATOS_POSTGRES_MIGRATOR_PASSWORD is required}"
: "${KRATOS_POSTGRES_RUNTIME_PASSWORD:?KRATOS_POSTGRES_RUNTIME_PASSWORD is required}"
: "${HYDRA_POSTGRES_MIGRATOR_PASSWORD:?HYDRA_POSTGRES_MIGRATOR_PASSWORD is required}"
: "${HYDRA_POSTGRES_RUNTIME_PASSWORD:?HYDRA_POSTGRES_RUNTIME_PASSWORD is required}"

psql \
    --username="${POSTGRES_USER}" \
    --dbname=postgres \
    --set=ON_ERROR_STOP=1 \
    --set=migrator_password="${BACKEND_POSTGRES_MIGRATOR_PASSWORD}" \
    --set=runtime_password="${BACKEND_POSTGRES_RUNTIME_PASSWORD}" \
    --file=/usr/local/share/otk-app-database/otk-app/init.sql

psql \
    --username="${POSTGRES_USER}" \
    --dbname=postgres \
    --set=ON_ERROR_STOP=1 \
    --set=migrator_password="${KRATOS_POSTGRES_MIGRATOR_PASSWORD}" \
    --set=runtime_password="${KRATOS_POSTGRES_RUNTIME_PASSWORD}" \
    --file=/usr/local/share/otk-app-database/kratos/init.sql

psql \
    --username="${POSTGRES_USER}" \
    --dbname=postgres \
    --set=ON_ERROR_STOP=1 \
    --set=migrator_password="${HYDRA_POSTGRES_MIGRATOR_PASSWORD}" \
    --set=runtime_password="${HYDRA_POSTGRES_RUNTIME_PASSWORD}" \
    --file=/usr/local/share/otk-app-database/hydra/init.sql
