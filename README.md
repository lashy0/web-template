# Web App

Monorepository for the Web App backend and its independently operated host
infrastructure.

## Project structure

```text
.
├── apps/                  Application source code
│   ├── backend/           FastAPI application, migrations, and tests
│   └── frontend/          React SPA, unit tests, and browser tests
├── packages/              Private TypeScript source packages
│   ├── api-client/        Generated OpenAPI client for the frontend
│   └── ui/                Shared shadcn/Base UI components and tokens
├── docs/                  Project and deployment documentation
├── infrastructure/        Compose projects and operational CLI
├── .env.example           Shared environment template
└── README.md
```

Detailed layouts and configuration are documented in:

- [Backend](apps/backend/README.md)
- [Frontend](apps/frontend/README.md)
- [Infrastructure](infrastructure/README.md)
- [Backend infrastructure](infrastructure/backend/README.md)
- [Frontend infrastructure](infrastructure/frontend/README.md)
- [Database](infrastructure/database/README.md)
- [Identity](infrastructure/identity/README.md)
- [Traefik](infrastructure/traefik/README.md)

## Local development

Create and review the shared environment file:

```console
cp .env.example .env
```

Configure the separate `infrastructure/traefik/.env` as described in the
[Traefik README](infrastructure/traefik/README.md).
Create the persistent Kratos secrets in `infrastructure/identity/.env` as
described in the [Identity README](infrastructure/identity/README.md).

Start infrastructure, then deploy the backend and frontend independently:

```console
uv run --project infrastructure infra-database up dev
uv run --project infrastructure infra-traefik up dev
uv run --project infrastructure infra-identity up dev
uv run --project infrastructure infra-application backend up dev
uv run --project infrastructure infra-application frontend up dev
```

Open <http://localhost:5173>. The frontend source and shared TypeScript package
changes reload automatically. Docker Desktop must be running.

PostgreSQL and Redis are exposed only on loopback in development. Application
deployment checks their health but never starts or updates them.

Normal shutdown uses the reverse order:

```console
uv run --project infrastructure infra-application frontend down dev
uv run --project infrastructure infra-application backend down dev
uv run --project infrastructure infra-identity down dev
uv run --project infrastructure infra-traefik down dev
uv run --project infrastructure infra-database down dev
```

Vite serves the development frontend on `http://localhost:5173` and proxies
`/api` to the backend through Traefik. Production serves the built SPA from
`app.${BASE_DOMAIN}`.
