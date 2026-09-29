# Identity infrastructure

This directory owns the independent `otk-app-identity` Compose project. It runs
Ory Kratos `v26.2.0` and Ory Hydra `v26.2.0` against the shared PostgreSQL
cluster, but its lifecycle is independent from both the database and application
projects.

## Configuration

`infra init` creates the ignored `.env` from `.env.example` and generates the
secrets; `KRATOS_CIPHER_SECRET` has exactly 32 characters.

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
uv run --project infrastructure infra database up dev
uv run --project infrastructure infra traefik up dev
uv run --project infrastructure infra identity up dev
```

`infra identity up` checks the `otk-app-database` and `traefik-public` networks,
creates the stack-owned external `otk-app-identity` network, runs SQL migrations,
and waits for Kratos and Hydra readiness. Use `--health-timeout` to change the
default 90-second wait.

Inspect or stop the stack independently:

```console
uv run --project infrastructure infra identity status dev
uv run --project infrastructure infra identity down dev
```

Replace `dev` with `prod` for production. Production has no host port mappings.
In development the Kratos Public API is reached through Traefik, as in
production; only its Admin API is bound to `127.0.0.1:4434`. Hydra's Admin API is bound to `127.0.0.1:4445`
in development only and is otherwise reachable only by containers on
`otk-app-identity`.

## Public contract

Ory shares the application host `${APP_HOST}` with the SPA (`/`) and the API
(`/api`) under the `/.ory` prefix, which Traefik removes before forwarding.
Traefik sends only these Kratos paths to the Public API:

- `/.ory/kratos/self-service/login` and `/.ory/kratos/self-service/login/*`
  (rate limited per source IP);
- `/.ory/kratos/self-service/logout` and `/.ory/kratos/self-service/logout/*`;
- `/.ory/kratos/self-service/errors` and `/.ory/kratos/self-service/errors/*`;
- `/.ory/kratos/sessions/whoami`;
- `/.ory/kratos/schemas` and `/.ory/kratos/schemas/*`.

Kratos's public base URL is `https://${APP_HOST}/.ory/kratos/`, so the flow
URLs it returns carry the prefix. Development uses the same routes over
`http://${APP_HOST}`.

Registration, recovery, verification, settings, and `/admin/*` are not routed
to Kratos. Kratos listens for its Admin API directly on internal TCP port 4434.
The port is bound to `127.0.0.1` only in development, is not published on the
host in production, and has no Traefik router.

## Hydra OAuth2 contract

Hydra supports OAuth2 `client_credentials` for PAKs. Traefik forwards only
`POST /.ory/hydra/oauth2/token` on `${APP_HOST}` to Hydra's Public API; the
issuer is `https://${APP_HOST}/.ory/hydra`. A PAK exchanges its credentials at
`https://<host>/.ory/hydra/oauth2/token` and calls the business endpoints under
`https://<host>/api/machine/`. The backend is not in the credential exchange
and never receives `client_secret`.

Access tokens use the opaque strategy and are checked through the Admin API's
introspection endpoint by the backend on `otk-app-identity`.

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

Application users, including the first administrator, are created through the
backend with `otk users create` (see the
[backend infrastructure](../backend/README.md)), which keeps the identity and
the local user together. An identity created directly through the Admin API
below has no local user and cannot sign in to the application.
Hydra readiness is checked by Compose over its internal Admin API.
