# Deployment

PostgreSQL/Redis, Traefik, Ory Kratos, the backend, and the frontend are separate Compose
projects. One Docker host represents one environment; dev and prod are not run
together on the same daemon.

The backend and frontend have their own runtime images and release tags. The
frontend image is an unprivileged Nginx image containing the React SPA. Traefik
serves the SPA at `app.${BASE_DOMAIN}` and routes
`app.${BASE_DOMAIN}/api/*` to the backend after removing the `/api` prefix. The
direct machine endpoint remains `api.${BASE_DOMAIN}`.

## Environment

Create `.env` in the repository root from `.env.example`. The important
production variables are:

| Variable | Required | Description |
| --- | --- | --- |
| `POSTGRES_ADMIN_PASSWORD` | yes | Password for the `postgres_admin` bootstrap and operations role |
| `POSTGRES_MIGRATOR_PASSWORD` | yes | Alembic DDL role |
| `POSTGRES_RUNTIME_PASSWORD` | yes | Backend DML role |
| `KRATOS_POSTGRES_MIGRATOR_PASSWORD` | yes | Kratos database owner and migration role |
| `KRATOS_POSTGRES_RUNTIME_PASSWORD` | yes | Least-privileged Kratos runtime role |
| `REDIS_ADMIN_PASSWORD` | yes | Redis operations and ACL management |
| `REDIS_RUNTIME_PASSWORD` | yes | Backend session access |
| `BACKEND_CORS_ORIGINS` | yes | JSON array of browser origins |
| `BACKEND_WORKERS` | no | Uvicorn workers; current capacity contract is four |
| `POSTGRES_MEMORY_LIMIT` | no | PostgreSQL container limit, default `2g` |

The database and backend services all receive the root `.env`; explicit
service overrides choose migrator or runtime identities. This simplifies
configuration but means privileged variables remain visible inside runtime
containers. Never commit `.env` or print effective Compose configuration in
production diagnostics.

Kratos cookie and cipher secrets are stored separately in the ignored
`infrastructure/identity/.env`. Generate them once from its `.env.example` and
preserve them across deployments.

## Startup and shutdown

Deploy in this order:

```console
uv run --project infrastructure infra-database up prod
uv run --project infrastructure infra-traefik up prod
uv run --project infrastructure infra-identity up prod
uv run --project infrastructure infra-application backend up prod
uv run --project infrastructure infra-application frontend up prod
```

The identity command checks its database and Traefik networks, applies Kratos
migrations, and waits for readiness. The backend command fails before
build/start if the `web-database` network or either healthy data-service
container is absent. It never invokes the database project. The `prestart`
container then applies Alembic migrations as `web_app_migrator`; the backend
connects as the runtime roles.

Shut down in reverse order. Database shutdown is guarded while application
containers remain active.

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
production backups must include the `web_app` and `kratos` databases, and a
backup is required before upgrading Kratos. Redis volume loss can invalidate
all sessions but must not lose business data.
