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

* [Database models and migrations](docs/database.md)

## Backend tests

Run the complete test suite with:

```console
uv run pytest
```

The available test markers are:

* `unit` - isolated tests with external dependencies mocked.
* `integration` - tests that verify the integration between application components.

## Migrations

Database migrations are managed with [Alembic](https://alembic.sqlalchemy.org/).

When the application is started with Docker Compose, pending migrations are
automatically applied by the `prestart` service before the backend starts.
