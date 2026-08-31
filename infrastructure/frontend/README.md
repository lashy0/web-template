# Frontend infrastructure

This directory owns the independent `web-frontend` Compose project. In
development it runs Vite at `http://localhost:5173`; in production it deploys
the immutable Nginx image built from `apps/frontend`.

## Structure

```text
frontend/
├── docker-compose.yaml       Shared image and network settings
├── docker-compose.dev.yaml   Vite development container and source mounts
├── docker-compose.prod.yaml  Production routing and health check
└── README.md                 Frontend infrastructure documentation
```

The base file contains settings shared by both environments. The dev and prod
files are overrides and are not intended to be used without the base file.

## Operations

Start Traefik before the frontend. In development, start the backend and
identity stacks first so Vite can proxy API and Kratos requests. Run the
following commands from the repository root:

```console
uv run --project infrastructure infra-application frontend up dev
uv run --project infrastructure infra-application frontend status dev
uv run --project infrastructure infra-application frontend down dev
```

The frontend has its own image tag and can be updated independently of the
backend:

```console
uv run --project infrastructure infra-application frontend up prod
```
