# Infrastructure

The application, database, and Traefik stacks are independent Docker Compose
projects managed through one uv environment.

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
uv run infra-application up dev
```

Use `status` with the same environment argument to inspect a project. Stop the
projects in reverse order:

```console
uv run infra-application down dev
uv run infra-traefik down dev
uv run infra-database down dev
```

Replace `dev` with `prod` when managing the production configuration.

## Documentation

Each independently operated project documents its configuration and lifecycle:

* [Application](application/README.md)
* [Database](database/README.md)
* [Traefik](traefik/README.md)
* [Deployment](../docs/deployment.md)

## Structure

```text
infrastructure/
├── cli/                    Shared lifecycle CLI
├── application/            Web application stack
├── database/               PostgreSQL and Redis stack
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
