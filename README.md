# Web App

Monorepository for the Web App services. Deployable applications live in
`apps/`, while repository-wide automation and operational utilities live in
`scripts/`.

## Repository structure

```text
.
├── apps/
│   └── backend/                 FastAPI application
├── scripts/                     Repository automation and operational tools
├── docker-compose.yaml          Shared service definitions
├── docker-compose.dev.yaml      Development overrides
└── docker-compose.prod.yaml     Production overrides
```

## Local development

Create the local environment file:

```console
cp .env.example .env
```

Review the values in `.env`, then start the development stack from the
repository root:

```console
docker compose -f docker-compose.yaml -f docker-compose.dev.yaml up --build --watch
```

The following services will be available:

* Backend API: <http://localhost:8000>
* PostgreSQL: `localhost:5432` by default
* Redis: `localhost:6379` by default

Stop the development stack:

```console
docker compose -f docker-compose.yaml -f docker-compose.dev.yaml down
```

## Applications

* [Backend](apps/backend/README.md) — FastAPI application, development setup,
  tests, migrations and documentation.

Read the application-specific README before changing an application.

## Production

Install Docker with the Compose plugin and uv, then create `.env` with
production values. Run the deployment script from the repository root:

```console
uv run --script scripts/deploy.py
```

Production secrets must not use the development defaults from `.env.example`.
