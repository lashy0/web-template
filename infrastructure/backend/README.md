# Backend infrastructure

This directory owns the independent `otk-app-backend` Compose project containing
the Litestar API, the SAQ task worker, and the `prestart` container that applies
migrations. It joins the external
`otk-app-database`, `otk-app-identity`, and `traefik-public` networks but never
creates or manages their services.

## Structure

```text
backend/
├── docker-compose.yaml       API, worker, prestart and external networks
├── docker-compose.dev.yaml   Backend debug mode and Compose file watching
├── docker-compose.prod.yaml  Production restarts and TLS routing
└── README.md                 Backend infrastructure documentation
```

The base file contains settings shared by both environments. The dev and prod
files are overrides and are not intended to be used without the base file.

## Configuration

The project loads the shared `.env` from the repository root. The `prestart`
container applies Alembic migrations as `otk_app_migrator`. The API and the
worker connect to PostgreSQL as `otk_app_runtime` and to Redis as
`otk_app_runtime`. All services use the same `otk-app-backend` image built from
`apps/backend`; their startup commands are kept in `apps/backend/scripts/`.

The worker runs the SAQ queue named after `BACKEND_REDIS_PREFIX`, including the
scheduled tasks. The API does not start workers of its own.

Requests below `/api` on `${APP_HOST}` are routed to the API with the prefix
kept: the application serves every route under `/api`. The container health
check calls `/api/health` and treats both 200 and 503 as alive, since 503 only
reports that PostgreSQL, Kratos or Hydra is unavailable.

## Operations

Start the database, identity, and Traefik projects before starting this project;
`infra up` starts everything in order. Manage this project from the repository
root:

```console
uv run --project infrastructure infra backend up dev
uv run --project infrastructure infra backend status dev
uv run --project infrastructure infra backend logs dev
uv run --project infrastructure infra backend down dev
```

`up` builds and starts the containers in the background and waits until they
are healthy. To automatically sync backend code changes, add `--watch`: the
command then keeps watching until `Ctrl+C`, and the containers keep running.

```console
uv run --project infrastructure infra backend up dev --watch
```

`up prod` builds the image of the checked-out release only once; deploying the
same release again, for example on a rollback, reuses it.

After the services are healthy, `up` runs `app users ensure-admin`: when no
active administrator exists, it creates the administrator `admin` with a
generated password, which `up` shows once after its summary.

## Backend commands

`otk` runs the backend CLI in the running API container, so operators never
enter the container and PostgreSQL and Kratos stay unpublished. Its arguments
are passed through unchanged:

```console
uv run --project infrastructure otk --help
uv run --project infrastructure otk users reset-password admin
uv run --project infrastructure otk users create --role operator
```

`reset-password` replaces a password with a generated one and ends the user's
sessions; `create` asks for the password.
