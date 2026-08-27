# Database infrastructure

This directory owns the independent `web-database` Compose project containing
PostgreSQL and Redis. The application joins its private external network, but
does not start, update, or stop either data service.

## Structure

```text
database/
├── postgres/
│   ├── init.sh                New-cluster initialization runner
│   ├── web-app/
│   │   └── init.sql           Web App database, roles and privileges
│   ├── kratos/
│   │   └── init.sql           Kratos database, roles and privileges
│   └── hydra/
│       └── init.sql           Hydra database, roles and privileges
├── redis/
│   ├── entrypoint.sh          Redis ACL rendering and server startup
│   └── users.acl.template     Redis users, permissions and key patterns
├── docker-compose.yaml        PostgreSQL, Redis, volumes and private network
├── docker-compose.dev.yaml    Loopback PostgreSQL and Redis ports
├── docker-compose.prod.yaml   Production memory limits and Redis policy
└── README.md                  Database infrastructure documentation
```

The PostgreSQL image runs `postgres/init.sh` from `/docker-entrypoint-initdb.d`
only when it initializes an empty data directory. The runner passes each
consumer's role passwords to its own SQL file. Those files explicitly create
the `web_app`, `kratos`, and `hydra` databases, their migrator and runtime roles, and the
required privileges. The dev and prod files only override
environment-specific container settings.

Initialization does not run again for an existing PostgreSQL volume. Changing
a role password or initialization SQL therefore requires an explicit database
administration operation; restarting the stack does not reconcile existing
roles or databases.

### Adding Hydra to an existing database volume

After deploying this change to a PostgreSQL volume that was initialized before
Hydra was added, create the new database and roles once before starting the
identity project. The PostgreSQL container already receives the required
passwords from the repository environment:

```console
docker compose exec postgres sh -c '\
  psql --username="$POSTGRES_USER" --dbname=postgres --set=ON_ERROR_STOP=1 \
    --set=migrator_password="$HYDRA_POSTGRES_MIGRATOR_PASSWORD" \
    --set=runtime_password="$HYDRA_POSTGRES_RUNTIME_PASSWORD" \
    --file=/usr/local/share/web-database/hydra/init.sql'
```

Run this only when the `hydra` database and its roles do not yet exist; the SQL
is intentionally strict so an accidental second invocation fails instead of
silently altering credentials. Hydra's own schema migration then runs as the
`hydra-migrate` identity service.

## Configuration

Both the database and application projects load the repository `.env` file.
Copy `.env.example` to `.env` and replace every example credential before use.
The fixed database and principal names are:

- database: `web_app`;
- PostgreSQL: `postgres_admin`, `web_app_migrator`, `web_app_runtime`;
- identity database: `kratos`;
- identity PostgreSQL: `kratos_migrator`, `kratos_runtime`;
- OAuth2 database: `hydra`;
- OAuth2 PostgreSQL: `hydra_migrator`, `hydra_runtime`;
- Redis: `web_app_admin`, `web_app_runtime`.

Each migrator role owns its database and public schema. The long-running
runtime roles have no DDL rights; initialization grants only
CONNECT, schema USAGE, table DML, sequence access, and matching default
privileges.

Because every service receives the shared environment file, runtime containers
can see credentials they do not use. Role-specific `BACKEND_*` overrides still
select the least-privileged login for each process, but this is not credential
isolation at the container boundary.

## Operations

Manage the database project from the repository root:

```console
uv run --project infrastructure infra-database up dev
uv run --project infrastructure infra-database status dev
uv run --project infrastructure infra-database down dev
```

Do not invoke application deployment as a substitute for starting this project.

PostgreSQL is the system of record. Redis persists AOF data so normal restarts
retain sessions, but loss of its volume may log out every user. There is no
off-host backup, WAL archive, point-in-time recovery, automated restore, or
guaranteed RPO/RTO. Loss of the PostgreSQL volume can therefore cause complete
business-data loss.
