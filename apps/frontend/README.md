# Frontend

The frontend is a React SPA served at `app.${BASE_DOMAIN}` in production. Vite
runs in its own Docker Compose project during development; production uses a
multi-stage image and an unprivileged Nginx runtime.

## Requirements

- Docker Desktop with Docker Compose
- The backend, identity, and Traefik development infrastructure

Start the frontend after the backend, Traefik, and identity development stacks:

```console
uv run --project infrastructure infra-application frontend up dev
```

Open <http://localhost:5173>. The container runs Vite and reloads changes in
the frontend and shared TypeScript packages automatically.

Browser requests to `/api/*` are proxied to `http://api.${BASE_DOMAIN}` with the
`/api` prefix removed. The application does not read a build-time API host.

## Quality checks

Run the repository quality gate:

```console
pnpm check
```

Run the Chromium end-to-end smoke test:

```console
pnpm test:e2e
```

The full release matrix is available from the frontend workspace:

```console
pnpm --filter @web-app/frontend test:e2e:full
```

## Structure

```text
src/
├── app/       Providers, router and global application configuration
├── routes/    TanStack Router file-based routes
└── test/      Shared Vitest setup
```

Shared design tokens and shadcn/Base UI components live in `packages/ui`.
Generated API code lives in `packages/api-client`. TanStack Form and charting
libraries are intentionally deferred until a product scenario needs them.
