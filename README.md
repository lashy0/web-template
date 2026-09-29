# Web App

Monorepository for the Web App backend and its independently operated host
infrastructure.

## Project structure

```text
.
├── apps/                  Application source code
│   ├── backend/           Litestar application, migrations, and tests
│   └── frontend/          React SPA
├── packages/              Private TypeScript source packages
│   ├── api-client/        Generated OpenAPI client for the frontend
│   └── ui/                Shared shadcn/Base UI components and tokens
├── docs/                  Project and deployment documentation
├── infrastructure/        Compose projects and operational CLI
├── .env.example           Shared environment template
└── README.md
```

Detailed layouts and configuration are documented in:

- [Backend](apps/backend/AGENTS.md)
- [Frontend](apps/frontend/README.md)
- [Infrastructure](infrastructure/README.md)
- [Backend infrastructure](infrastructure/backend/README.md)
- [Frontend infrastructure](infrastructure/frontend/README.md)
- [Database](infrastructure/database/README.md)
- [Identity](infrastructure/identity/README.md)
- [Traefik](infrastructure/traefik/README.md)

## Local development

Create the ignored environment files and their secrets:

```console
uv run --project infrastructure infra init
```

`infra init` creates `.env`, `infrastructure/identity/.env` and
`infrastructure/traefik/.env` from their examples and generates every secret;
the Traefik dashboard password is in a comment in `infrastructure/traefik/.env`.
It never changes existing values, so it can be run again when an example gains
a variable.

Start everything in dependency order and keep syncing backend code changes:

```console
uv run --project infrastructure infra up dev --watch
```

`Ctrl+C` stops only the sync; the containers keep running. On the first start,
the command creates the administrator `admin` and shows its generated password
once. A lost password is replaced with:

```console
uv run --project infrastructure otk users reset-password admin
```

Open <http://localhost>. Traefik routes the one host `${APP_HOST}` as in
production: `/` to the Vite dev server, `/api` to the backend and `/.ory` to
Kratos and Hydra. The frontend source and shared TypeScript package changes
reload automatically. Docker Desktop must be running.

PostgreSQL and Redis are exposed only on loopback in development. Application
deployment checks their health but never starts or updates them.

Stop everything in reverse order; the data volumes are kept:

```console
uv run --project infrastructure infra down dev
```

Each project can also be managed alone, for example `infra backend logs dev`
or `infra frontend up dev`; see the [infrastructure README](infrastructure/README.md).
