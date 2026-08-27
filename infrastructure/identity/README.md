# Identity infrastructure

This directory owns the independent `web-identity` Compose project. It runs
Ory Kratos `v26.2.0` and Ory Hydra `v26.2.0` against the shared PostgreSQL
cluster, but its lifecycle is independent from both the database and application
projects.

## Configuration

Copy the identity secret template once and replace all values:

```console
cp .env.example .env
openssl rand -hex 32  # KRATOS_COOKIE_SECRET
openssl rand -hex 16  # KRATOS_CIPHER_SECRET, exactly 32 characters
openssl rand -hex 32  # HYDRA_SYSTEM_SECRET
```

Do not regenerate these values during deployment. Rotation needs an explicit
plan because changing them invalidates cookies, encrypted data, or OAuth2
signing state. The ignored identity `.env` contains Kratos cookie/cipher secrets
and the Hydra system secret. PostgreSQL passwords remain in the repository root
`.env`:

- `KRATOS_POSTGRES_MIGRATOR_PASSWORD` owns the `kratos` database and applies
  migrations;
- `KRATOS_POSTGRES_RUNTIME_PASSWORD` is used by the long-running server and is
  limited to connection, schema usage, DML, and sequence access.
- `HYDRA_POSTGRES_MIGRATOR_PASSWORD` owns the `hydra` database and applies
  migrations;
- `HYDRA_POSTGRES_RUNTIME_PASSWORD` is used by the long-running Hydra server
  with the same restricted database permissions.

Passwords placed in a PostgreSQL DSN must be URL-safe. Hex-generated values are
recommended.

## Operations

Start the projects in dependency order:

```console
uv run --project infrastructure infra-database up dev
uv run --project infrastructure infra-traefik up dev
uv run --project infrastructure infra-identity up dev
```

`infra-identity up` checks the `web-database` and `traefik-public` networks,
creates the stack-owned external `web-identity` network, runs SQL migrations,
and waits for Kratos and Hydra readiness. Use `--health-timeout` to change the
default 90-second wait.

Inspect or stop the stack independently:

```console
uv run --project infrastructure infra-identity status dev
uv run --project infrastructure infra-identity down dev
```

Replace `dev` with `prod` for production. Production has no host port mappings.
Development binds Kratos's Public and Admin APIs only to `127.0.0.1:4433` and
`127.0.0.1:4434` respectively. Hydra has no host port mappings: its Public API
is served through Traefik at `http://oauth.${BASE_DOMAIN}` and its Admin API is
reachable only by containers on `web-identity`.

## Public contract

Traefik sends only these native Kratos paths on `app.${BASE_DOMAIN}` to the
Public API:

- `/self-service/login` and `/self-service/login/*` (rate limited per source IP);
- `/self-service/logout` and `/self-service/logout/*`;
- `/self-service/errors` and `/self-service/errors/*`;
- `/sessions/whoami`;
- `/schemas` and `/schemas/*`.

Registration, recovery, verification, settings, and `/admin/*` are not routed
to Kratos. Kratos listens for its Admin API directly on internal TCP port 4434.
The port is bound to `127.0.0.1` only in development, is not published on the
host in production, and has no Traefik router.

## Hydra OAuth2 contract

Hydra's public API is routed at `oauth.${BASE_DOMAIN}`. It supports OAuth2
`client_credentials`, including `POST /oauth2/token`; the configured issuer is
the same public URL. Access tokens use the opaque strategy and must be checked
through the Admin API's introspection endpoint by a service on `web-identity`.

Hydra's Admin API listens only on internal TCP port 4445. It has no host port
mapping and no Traefik router. Backend containers use `http://hydra:4445` for
OAuth2 client provisioning, credential rotation, and token introspection.

The identity schema accepts one required password identifier named `login`.
It must be lowercase ASCII, between 3 and 64 characters, and match
`^[a-z0-9][a-z0-9._-]{2,63}$`.

## Creating an identity

Operators can create a login with an initial password through the loopback
Admin API in development:

```console
curl --request POST http://127.0.0.1:4434/admin/identities \
  --header "Content-Type: application/json" \
  --data '{"schema_id":"default","traits":{"login":"operator"},"credentials":{"password":{"config":{"password":"replace-with-12+-character-password"}}}}'
```

In production, run the equivalent request from an authorized internal service
sharing a Docker network with Kratos; never publish port 4434 or add an Admin
API Traefik router without adding authentication and authorization.

## Verification

Validate the merged Compose models without starting containers:

```console
docker compose --env-file ../../.env --env-file .env \
  -f docker-compose.yaml -f docker-compose.dev.yaml config --quiet
docker compose --env-file ../../.env --env-file .env \
  -f docker-compose.yaml -f docker-compose.prod.yaml config --quiet
```

After a development deployment, check readiness at
`http://127.0.0.1:4434/health/ready`. Public smoke tests should exercise login,
`whoami`, logout, the route allowlist, and the login rate limit through Traefik.
Hydra readiness is checked by Compose over its internal Admin API.
