#!/usr/bin/env bash

set -euo pipefail

: "${REDIS_ADMIN_PASSWORD:?REDIS_ADMIN_PASSWORD is required}"
: "${REDIS_RUNTIME_PASSWORD:?REDIS_RUNTIME_PASSWORD is required}"

ACL_TEMPLATE="/usr/local/share/web-database/users.acl.template"
ACL_DIRECTORY="/run/web-database-redis"
ACL_FILE="${ACL_DIRECTORY}/users.acl"

hash_password() {
    local password_hash

    password_hash="$(printf '%s' "$1" | sha256sum)"
    printf '%s' "${password_hash%% *}"
}

ADMIN_PASSWORD_HASH="$(hash_password "${REDIS_ADMIN_PASSWORD}")"
RUNTIME_PASSWORD_HASH="$(hash_password "${REDIS_RUNTIME_PASSWORD}")"

umask 077
mkdir -p "${ACL_DIRECTORY}"

sed \
    -e "s/__ADMIN_PASSWORD_HASH__/${ADMIN_PASSWORD_HASH}/g" \
    -e "s/__RUNTIME_PASSWORD_HASH__/${RUNTIME_PASSWORD_HASH}/g" \
    "${ACL_TEMPLATE}" >"${ACL_FILE}"

chown redis:redis "${ACL_DIRECTORY}" "${ACL_FILE}"

exec docker-entrypoint.sh redis-server --aclfile "${ACL_FILE}" "$@"
