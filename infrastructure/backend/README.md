# Backend infrastructure

This directory owns the independent `web-backend` Compose project containing
the FastAPI backend and its migration prestart container. It joins the external
`web-database`, `web-identity`, and `traefik-public` networks but never creates
or manages their services.

## Structure

```text
backend/
├── docker-compose.yaml       Backend, prestart and external networks
├── docker-compose.dev.yaml   Backend debug mode and Compose file watching
├── docker-compose.prod.yaml  Production restarts and TLS routing
└── README.md                 Backend infrastructure documentation
```

The base file contains settings shared by both environments. The dev and prod
files are overrides and are not intended to be used without the base file.

## Configuration

The project loads the shared `.env` from the repository root. The prestart
container connects to PostgreSQL as `web_app_migrator`; the backend connects to
PostgreSQL and Redis as `web_app_runtime`.

Requests below `/api` on `app.${BASE_DOMAIN}` are routed directly to the backend
with the prefix removed. Machines can continue to use `api.${BASE_DOMAIN}`.
The frontend is an independent Compose project in
[`../frontend`](../frontend/README.md).

## Operations

Start the database, identity, and Traefik projects before starting this project.
Manage this project from the repository root:

```console
uv run --project infrastructure infra-application backend up dev
uv run --project infrastructure infra-application backend status dev
uv run --project infrastructure infra-application backend down dev
```
