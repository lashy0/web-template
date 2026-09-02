# Frontend API client

This private source package contains the generated client used by
`@web-app/frontend`. It is not a machine-to-machine SDK.

Export the frontend-facing FastAPI OpenAPI document and generate the client:

```console
pnpm api:generate
```

The exported `openapi.json` contains only the `web` audience. The OpenAPI snapshot
and generated files are committed and must not be edited, linted, or formatted
manually.

The schema is exported directly from the backend application, so the backend and
its external dependencies do not need to be running.
