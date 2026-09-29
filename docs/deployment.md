# Deployment

PostgreSQL/Redis, Traefik, Ory Kratos, the backend, and the frontend are separate Compose
projects. One Docker host represents one environment; dev and prod are not run
together on the same daemon.

The backend and frontend have their own runtime images, tagged with the same
release version. The frontend image is an unprivileged Nginx image containing
the React SPA.

Everything public is served from one host, `${APP_HOST}`:

| Path | Destination |
| --- | --- |
| `/` | SPA (frontend) |
| `/api/*` | backend, prefix kept |
| `/.ory/kratos/*` | Kratos public API (listed browser flows only), prefix removed |
| `/.ory/hydra/oauth2/token` | Hydra token endpoint for PAKs, prefix removed |

The Traefik dashboard is not on this host; it listens on the server's
local-network address only (see the [Traefik README](../infrastructure/traefik/README.md)).

The PAK machine API is documented in the
[verification guide](../apps/backend/docs/domain/verification.md). The public
OAuth2 routing is documented by the
[identity infrastructure](../infrastructure/identity/README.md).

## Environment

Create the environment files with `uv run --project infrastructure infra init`. It
generates every secret and never changes existing values. The important
production variables are:

| Variable | Required | Description |
| --- | --- | --- |
| `APP_HOST` | yes | The public host of the SPA, API and Ory, e.g. `otk.example.com` |
| `POSTGRES_ADMIN_PASSWORD` | yes | Password for the `postgres_admin` bootstrap and operations role |
| `BACKEND_POSTGRES_MIGRATOR_PASSWORD` | yes | Alembic DDL role |
| `BACKEND_POSTGRES_RUNTIME_PASSWORD` | yes | Backend DML role |
| `KRATOS_POSTGRES_MIGRATOR_PASSWORD` | yes | Kratos database owner and migration role |
| `KRATOS_POSTGRES_RUNTIME_PASSWORD` | yes | Least-privileged Kratos runtime role |
| `REDIS_ADMIN_PASSWORD` | yes | Redis operations and ACL management |
| `REDIS_RUNTIME_PASSWORD` | yes | Backend task queue access |
| `BACKEND_PAK_ACCESS_KEY_ENCRYPTION_KEY` | yes | Fernet key encrypting PAK access keys |
| `BACKEND_WORKERS` | no | Uvicorn workers; current capacity contract is four |
| `POSTGRES_MEMORY_LIMIT` | no | PostgreSQL container limit, default `2g` |

The database and backend services all receive the root `.env`; explicit
service overrides choose migrator or runtime identities. This simplifies
configuration but means privileged variables remain visible inside runtime
containers. Never commit `.env` or print effective Compose configuration in
production diagnostics.

Kratos cookie and cipher secrets are stored separately in the ignored
`infrastructure/identity/.env`. `infra init` generates them once; preserve
them across deployments.

## Releases

A release version is CalVer `YEAR.MONTH.N` without leading zeros, such as
`2026.9.2`: the second release of September 2026. The git tag `v2026.9.2` is
its only source; the versions in `pyproject.toml` and `package.json` are not
used.

Tag the next release on a clean, committed HEAD and publish the tag:

```console
uv run --project infrastructure infra release --push
```

`up prod` builds only a clean checkout of a release tag and fails otherwise.
Both images are tagged with the version, and the backend reports it at
`GET /api/system/version`. Development builds report `dev`. To roll back,
check out the previous tag and run `infra up prod` again, keeping the migration
rules below in mind: an image is built once per release, so the previous images
are reused without a rebuild.

## Startup and shutdown

Deploy a release with one command:

```console
uv run --project infrastructure infra up prod
```

It starts the database, Traefik, identity, backend and frontend projects in this
order and waits until each is healthy; a failed health check stops the
deployment with an error. Each project can also be deployed alone, for example
`infra backend up prod`.

The identity command checks its database and Traefik networks, applies Kratos
migrations, and waits for readiness. The backend command fails before
build/start if the `otk-app-database` network or either healthy data-service
container is absent. It never invokes the database project. The `prestart`
container then applies Alembic migrations as `otk_app_migrator`; the API and
the worker connect as the runtime roles.

When no active administrator exists, the backend deployment creates the
administrator `admin` with a generated password and shows it once after the
summary. Sign in and keep the password, or replace a lost one:

```console
uv run --project infrastructure otk users reset-password admin
```

`otk` passes its arguments to the backend CLI in the running API container
(`uv run --project infrastructure otk --help` lists the commands).

`infra down prod` shuts down in reverse order. `infra database down` refuses
while other projects still use the databases.

## Schema releases and capacity

Production migrations follow expand-and-contract: a release must not remove or
rename objects required by the previous backend version. Destructive cleanup
belongs in a later release after the rollback window.

One backend replica with four workers, pool size five, and overflow five can
open 40 PostgreSQL connections. PostgreSQL permits 100. Adding replicas requires
a capacity review; PgBouncer is not part of the current topology.

## Recovery limitations

There are no off-host backups, WAL archiving, point-in-time recovery, automated
restore, replication, or failover. No RPO or RTO is guaranteed for host/storage
loss. PostgreSQL volume loss can lose both application and identity data;
production backups must include the `otk_app` and `kratos` databases, and a
backup is required before upgrading Kratos. Redis volume loss can lose queued
background jobs but must not lose business data; browser sessions live in
Kratos.

## Switching from the FastAPI backend

The Litestar backend has its own migration history and does not migrate the
FastAPI schema. It is deployed on new databases: an empty `otk_app` and, so
that no identity is left without a local user, an empty `kratos`. Data of the
FastAPI backend is not carried over.

The frontend and Traefik Compose projects were renamed from `web-frontend` and
`web-proxy` to `otk-app-frontend` and `otk-app-traefik`. On a host still
running the old projects, stop them first with
`docker compose -p web-proxy down` and `docker compose -p web-frontend down`.
Traefik then requests its certificate once more, because its ACME volume is
new.
