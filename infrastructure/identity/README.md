# Identity infrastructure

This directory owns the independent `web-identity` Compose project. It runs
Ory Kratos `v26.2.0` against the shared PostgreSQL cluster, but its lifecycle is
independent from both the database and application projects.

## Configuration

Copy the identity secret template once and replace both values:

```console
cp .env.example .env
openssl rand -hex 32  # KRATOS_COOKIE_SECRET
openssl rand -hex 16  # KRATOS_CIPHER_SECRET, exactly 32 characters
```

Do not regenerate these values during deployment. Rotation needs an explicit
plan because changing them invalidates cookies or encrypted data. The ignored
identity `.env` contains only Kratos cookie and cipher secrets. PostgreSQL
passwords remain in the repository root `.env`:

- `KRATOS_POSTGRES_MIGRATOR_PASSWORD` owns the `kratos` database and applies
  migrations;
- `KRATOS_POSTGRES_RUNTIME_PASSWORD` is used by the long-running server and is
  limited to connection, schema usage, DML, and sequence access.

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
and waits for Kratos readiness. Use `--health-timeout` to change the default
90-second wait.

Inspect or stop the stack independently:

```console
uv run --project infrastructure infra-identity status dev
uv run --project infrastructure infra-identity down dev
```

Replace `dev` with `prod` for production. Production has no host port mappings.
Development binds the Public and Admin APIs only to `127.0.0.1:4433` and
`127.0.0.1:4434` respectively.

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
