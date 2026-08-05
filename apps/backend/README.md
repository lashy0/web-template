# Backend

## Requirements

* [Docker](https://www.docker.com/).
* [uv](https://docs.astral.sh/uv/) for Python package and environment management.

## General Workflow

By default, the dependencies are managed with [uv](https://docs.astral.sh/uv/), go there and install it.
From `./apps/backend/` you can install all the dependencies with:

```console
uv sync
```

## Documentation

Development documentation lives in [`docs/`](docs/). Read the relevant guide
before changing the corresponding part of the backend:

* [Configuration](docs/configuration.md)
* [Database models and migrations](docs/database.md)
* [Redis](docs/redis.md)

## Backend tests

Run the fast test suite with:

```console
uv run pytest
```

Integration tests are excluded by default because they require real Postgres
and Redis services. With those dependencies available, run the integration
suite from `apps/backend/` with the repository environment loaded:

```console
uv run --env-file ../../.env pytest -m integration
```

The available test markers are:

* `unit` - isolated functions and classes with dependencies mocked.
* `api` - in-process FastAPI HTTP tests with external dependencies mocked.
* `integration` - tests against real external services.
* `slow` - tests intentionally excluded from time-sensitive workflows.

Tests are organized by scope first and then by feature:

```text
tests/
├── unit/
├── api/
└── integration/
```

## Migrations

Database migrations are managed with [Alembic](https://alembic.sqlalchemy.org/).

Apply pending migrations from `apps/backend/` with:

```console
uv run alembic upgrade head
```

Production migrations must follow expand-and-contract so the previous backend
remains compatible throughout the rollback window.
