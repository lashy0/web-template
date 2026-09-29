# Frontend infrastructure

This directory owns the independent `otk-app-frontend` Compose project.
Traefik serves it on `${APP_HOST}` for every path that `/api` and `/.ory` do
not claim: in development it runs the Vite dev server, in production the
immutable Nginx image built from `apps/frontend`.

## Structure

```text
frontend/
├── docker-compose.yaml       Shared image, network and routing
├── docker-compose.dev.yaml   Vite development container and source mounts
├── docker-compose.prod.yaml  Production TLS routing and health check
└── README.md                 Frontend infrastructure documentation
```

The base file contains settings shared by both environments. The dev and prod
files are overrides and are not intended to be used without the base file.

## Operations

Start Traefik before the frontend. The SPA calls `/api` and `/.ory` on its own
host, so a working application needs the backend and identity projects as well;
`infra up` starts everything in order. Run the following commands from the
repository root:

```console
uv run --project infrastructure infra frontend up dev
uv run --project infrastructure infra frontend status dev
uv run --project infrastructure infra frontend logs dev
uv run --project infrastructure infra frontend down dev
```

In development the sources of the frontend and the shared packages are mounted
into the container, and Vite reloads them over its WebSocket through Traefik.
`logs` shows the Vite output.

The frontend has its own image and can be updated independently of the
backend:

```console
uv run --project infrastructure infra frontend up prod
```
