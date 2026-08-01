# Deployment

The production stack is defined by the shared `docker-compose.yaml` file and the
`docker-compose.prod.yaml` overrides. The deployment script builds the backend image,
applies pending database migrations, and starts the services.

## Requirements

Install the following tools on the target host:

* Docker with the Compose plugin;
* uv.

## Environment

Create a `.env` file in the repository root. Use `.env.example` as a structural
reference, but replace development values and example secrets.

The production Compose configuration uses these deployment variables:

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `POSTGRES_DB` | yes | none | PostgreSQL database created for the application |
| `POSTGRES_USER` | yes | none | PostgreSQL application user |
| `POSTGRES_PASSWORD` | yes | none | PostgreSQL password |
| `REDIS_PASSWORD` | yes | none | Redis password |
| `BACKEND_CORS_ORIGINS` | yes | none | JSON array of allowed browser origins; use `[]` when CORS is not needed |
| `BACKEND_PORT` | no | `8000` | Host port mapped to backend port `8000` |
| `BACKEND_WORKERS` | no | `1` | Number of Uvicorn worker processes |
| `POSTGRES_MEMORY_LIMIT` | no | `2g` | PostgreSQL container memory limit |
| `REDIS_MEMORY_LIMIT` | no | `512m` | Redis container memory limit |

`BACKEND_DEBUG` is forced to `false` by the production Compose configuration. The
deployment script sets `TAG` from the backend version in `apps/backend/pyproject.toml`.
It does not need to be added to `.env` when the script is used.

Other backend settings are documented in
[`apps/backend/docs/configuration.md`](../apps/backend/docs/configuration.md), with
database and Redis client settings in their respective backend guides.

Example:

```env
POSTGRES_DB=web_app
POSTGRES_USER=web_app
POSTGRES_PASSWORD=replace-with-a-secret
REDIS_PASSWORD=replace-with-a-secret

BACKEND_CORS_ORIGINS=["https://app.example.com"]
BACKEND_PORT=8000
BACKEND_WORKERS=4
```

Do not commit `.env` or copy the development passwords from `.env.example` to a
deployed environment.

## Deploy

Run the deployment script from the repository root:

```console
uv run --script scripts/deploy.py
```

The script performs the equivalent of starting the shared and production Compose
files with `up -d --build`. The `prestart` service must finish the database migrations
successfully before the backend service starts.

## Inspect the deployment

Show service state:

```console
docker compose -f docker-compose.yaml -f docker-compose.prod.yaml ps
```

Show backend logs:

```console
docker compose -f docker-compose.yaml -f docker-compose.prod.yaml logs backend
```

Show migration logs:

```console
docker compose -f docker-compose.yaml -f docker-compose.prod.yaml logs prestart
```
