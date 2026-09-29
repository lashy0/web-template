# Frontend API client

This private source package contains the generated client used by
`@web-app/frontend`. It is not a machine-to-machine SDK.

Export the OpenAPI document of the Litestar backend and generate the client:

```console
pnpm api:generate
```

`openapi.json` is the whole backend contract, exported with
`app schema openapi`; the backend and its external services do not need to be
running. The client leaves out the PAK machine API and the health check
(`parser.filters` in `openapi-ts.config.ts`). The snapshot and generated files
are committed and must not be edited, linted, or formatted manually;
`pnpm api:check` fails when they are out of date.

The package exports:

- SDK functions and types, such as `listUsers` and `User`; enums are objects,
  so `Object.values(UserRole)` lists the roles.
- zod schemas with the backend's field rules, such as `zUserCreate`. Forms
  build on their fields (`zUserCreate.shape.login`); the Russian messages and
  helpers are in `apps/frontend/src/lib/validation.ts`. The backend describes
  where the rules come from in `apps/backend/docs/validation.md`.
  `openapi-ts.config.ts` moves the rules of optional fields into the string
  branch of their `oneOf`, where the generator reads them.
- TanStack Query options, such as `listUsersOptions`, `listUsersQueryKey` and
  `createUserMutation`. Query keys carry the operation tags, so
  `queryClient.invalidateQueries({ queryKey: [{ tags: ['Batches'] }] })`
  invalidates every query of that section.
- `configureApiClient` and `isApiError`. Queries and mutations throw the error
  body of the backend; `isApiError(error, 'login_already_exists')` checks its
  `extra.code`.
