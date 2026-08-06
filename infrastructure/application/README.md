# Application infrastructure

This directory owns the independent `web-app` Compose project containing the
backend, its migration prestart container, and the production frontend. It joins the external
`web-database` and `traefik-public` networks but never creates or manages their
services.

## Structure

```text
application/
├── docker-compose.yaml       Backend, prestart and external networks
├── docker-compose.dev.yaml   Backend debug mode and Compose file watching
├── docker-compose.prod.yaml  Frontend, production restarts and TLS routing
└── README.md                 Application infrastructure documentation
```

The base file contains settings shared by both environments. The dev and prod
files are overrides and are not intended to be used without the base file.

## Configuration

The project loads the shared `.env` from the repository root. The prestart
container connects to PostgreSQL as `web_app_migrator`; the backend connects to
PostgreSQL and Redis as `web_app_runtime`.

Production serves the React SPA from `app.${BASE_DOMAIN}`. Requests below
`/api` on that host are routed directly to the backend with the prefix removed.
Machines can continue to use `api.${BASE_DOMAIN}`. The development Compose
configuration does not start a frontend container; run Vite on the host with
`pnpm dev`.

## Operations

Start the database and Traefik projects before starting this project. Stop the
three projects in reverse order. Manage this project from the repository root:

```console
uv run --project infrastructure infra-application up dev
uv run --project infrastructure infra-application status dev
uv run --project infrastructure infra-application down dev
```
