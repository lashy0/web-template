# Frontend

The frontend is a React SPA served at `app.${BASE_DOMAIN}` in production. Vite
runs on the host during development; production uses a multi-stage image and an
unprivileged Nginx runtime.

## Requirements

- Node.js 24 LTS
- Corepack with the repository's pinned pnpm version
- The backend and Traefik development infrastructure for API proxying

Install workspace dependencies from the repository root:

```console
corepack pnpm install
```

Start Vite:

```console
pnpm dev
```

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
