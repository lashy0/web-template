# Frontend

The frontend is a React SPA served at `https://${APP_HOST}/` in production. Vite
runs in its own Docker Compose project during development; production uses a
multi-stage image and an unprivileged Nginx runtime.

## Requirements

- Docker Desktop with Docker Compose
- The backend, identity, and Traefik development infrastructure

Start the whole development stack, the frontend included:

```console
uv run --project infrastructure infra up dev
```

Open <http://localhost>. The container runs Vite and reloads changes in the
frontend and shared TypeScript packages automatically.

The SPA, the API and Ory share one host, as in production: Traefik routes `/`
to Vite, `/api/*` to the backend and `/.ory/*` to Kratos and Hydra. Vite
proxies nothing itself, and the application does not read a build-time API
host.

## Quality checks

Run the repository quality gate, which type-checks, lints, checks formatting and
builds every package:

```console
pnpm check
```

The frontend has no automated tests yet.

## Structure

```text
src/
├── app/         Providers, router and global application configuration
├── components/  Screens and dialogs, grouped by section
├── features/    Labels, form schemas and query helpers of each domain
├── lib/         Shared helpers: list search, validation messages, dates
└── routes/      TanStack Router file-based routes
```

Requests, query options, mutations and the zod schemas of request bodies are
generated in `packages/api-client`; see its README. Shared design tokens and
shadcn/Base UI components live in `packages/ui`.
