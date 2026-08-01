# Configuration

The backend reads its settings from environment variables. Variable names are
case-sensitive. Empty values are ignored, so the documented default is used instead.

| Variable | Default | Description |
| --- | --- | --- |
| `BACKEND_API_PREFIX` | empty | URL prefix for all API routes, for example `/api`; must start with `/` and must not end with `/` |
| `BACKEND_PROJECT_NAME` | `backend` | Application name used in OpenAPI metadata and structured logs |
| `BACKEND_DEBUG` | `false` | Enables FastAPI debug mode and detailed Loguru diagnostics |
| `BACKEND_LOG_LEVEL` | `INFO` | Minimum Loguru level written by the backend |
| `BACKEND_LOG_JSON` | `false` | Writes serialized JSON logs when enabled |
| `BACKEND_CORS_ORIGINS` | `[]` | JSON array of browser origins allowed to access the API cross-origin |

Database settings are documented in [database.md](database.md#configuration).
Redis settings are documented in [redis.md](redis.md#configuration).

## CORS origins

`BACKEND_CORS_ORIGINS` accepts one format: a JSON array of HTTP or HTTPS origins.
Each origin consists of a scheme, hostname, and optional port. Paths, credentials,
query strings, and fragments are rejected.

```env
BACKEND_CORS_ORIGINS=["https://app.example.com","https://admin.example.com"]
```

For a local frontend with an explicit port:

```env
BACKEND_CORS_ORIGINS=["http://localhost:5173"]
```

Use an empty JSON array when cross-origin browser access is not needed:

```env
BACKEND_CORS_ORIGINS=[]
```

Each origin is a JSON string, so it must be enclosed in double quotes.
