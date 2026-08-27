#!/usr/bin/env bash

set -euo pipefail

: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_MIGRATOR_PASSWORD:?POSTGRES_MIGRATOR_PASSWORD is required}"
: "${POSTGRES_RUNTIME_PASSWORD:?POSTGRES_RUNTIME_PASSWORD is required}"
: "${KRATOS_POSTGRES_MIGRATOR_PASSWORD:?KRATOS_POSTGRES_MIGRATOR_PASSWORD is required}"
: "${KRATOS_POSTGRES_RUNTIME_PASSWORD:?KRATOS_POSTGRES_RUNTIME_PASSWORD is required}"
: "${HYDRA_POSTGRES_MIGRATOR_PASSWORD:?HYDRA_POSTGRES_MIGRATOR_PASSWORD is required}"
: "${HYDRA_POSTGRES_RUNTIME_PASSWORD:?HYDRA_POSTGRES_RUNTIME_PASSWORD is required}"

psql \
    --username="${POSTGRES_USER}" \
    --dbname=postgres \
    --set=ON_ERROR_STOP=1 \
    --set=migrator_password="${POSTGRES_MIGRATOR_PASSWORD}" \
    --set=runtime_password="${POSTGRES_RUNTIME_PASSWORD}" \
    --file=/usr/local/share/web-database/web-app/init.sql

psql \
    --username="${POSTGRES_USER}" \
    --dbname=postgres \
    --set=ON_ERROR_STOP=1 \
    --set=migrator_password="${KRATOS_POSTGRES_MIGRATOR_PASSWORD}" \
    --set=runtime_password="${KRATOS_POSTGRES_RUNTIME_PASSWORD}" \
    --file=/usr/local/share/web-database/kratos/init.sql

psql \
    --username="${POSTGRES_USER}" \
    --dbname=postgres \
    --set=ON_ERROR_STOP=1 \
    --set=migrator_password="${HYDRA_POSTGRES_MIGRATOR_PASSWORD}" \
    --set=runtime_password="${HYDRA_POSTGRES_RUNTIME_PASSWORD}" \
    --file=/usr/local/share/web-database/hydra/init.sql
