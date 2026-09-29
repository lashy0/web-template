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

`infra` is the one operational command. Create the environment files once,
then start and stop the whole stack:

```console
uv run infra init
uv run infra up dev
uv run infra status dev
uv run infra down dev
```

`up` starts the projects in dependency order (database, Traefik, identity,
backend, frontend) and waits until each is healthy; `down` stops them in
reverse order. `up dev --watch` keeps syncing backend source changes
afterwards.

Every project can also be managed alone with the same commands:

```console
uv run infra database up dev
uv run infra backend up dev --watch
uv run infra backend logs dev api
uv run infra frontend logs dev
```

`infra database down` refuses while other projects still use the databases;
`--force` overrides the check.

Replace `dev` with `prod` when managing the production configuration.
`up prod` deploys only a clean checkout of a release tag; tag the next CalVer
release with `uv run infra release` (see
[deployment](../docs/deployment.md#releases)).

`infra up` and `infra backend up` create the administrator `admin` when no
active administrator exists and show its generated password once. `otk` runs
backend commands in the running API container, for example to replace a lost
password:

```console
uv run otk users reset-password admin
```

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
