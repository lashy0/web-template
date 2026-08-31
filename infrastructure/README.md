# Infrastructure

The frontend, backend, database, identity, and Traefik stacks are independent Docker
Compose projects managed through one uv environment.

## Requirements

* [Docker](https://www.docker.com/) with Docker Compose.
* [uv](https://docs.astral.sh/uv/) for the infrastructure CLI environment.

## General Workflow

From `./infrastructure/`, install the CLI and its dependencies with:

```console
uv sync
```

Complete the environment setup described in the
[repository README](../README.md#local-development), then start the independent
projects in operational order:

```console
uv run infra-database up dev
uv run infra-traefik up dev
uv run infra-identity up dev
uv run infra-application backend up dev
uv run infra-application frontend up dev
```

Use `status` with the same environment argument to inspect a project. Stop the
projects in reverse order:

```console
uv run infra-application frontend down dev
uv run infra-application backend down dev
uv run infra-identity down dev
uv run infra-traefik down dev
uv run infra-database down dev
```

Replace `dev` with `prod` when managing the production configuration.

## Documentation

Each independently operated project documents its configuration and lifecycle:

* [Backend](backend/README.md)
* [Frontend](frontend/README.md)
* [Database](database/README.md)
* [Identity](identity/README.md)
* [Traefik](traefik/README.md)
* [Deployment](../docs/deployment.md)

## Structure

```text
infrastructure/
├── cli/                    Shared lifecycle CLI
├── backend/                Backend stack
├── database/               PostgreSQL and Redis stack
├── frontend/               Frontend stack
├── identity/               Ory Kratos stack
└── traefik/                Reverse-proxy stack
```

Each Compose project owns its base, development, and production configuration.
The `cli` package provides their operational interface without merging their
lifecycles.

## Static checks

Run static checks from `./infrastructure/`:

```console
uv run ruff check cli
uv run mypy cli
uv run ty check cli
```
