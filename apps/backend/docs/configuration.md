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
| `BACKEND_READINESS_TIMEOUT` | `2.0` | Maximum duration in seconds for each PostgreSQL and Redis readiness check; must be greater than zero |
| `BACKEND_KRATOS_PUBLIC_URL` | `http://kratos:4433` | Internal Kratos Public API URL used for browser session verification |
| `BACKEND_KRATOS_ADMIN_URL` | `http://kratos:4434` | Internal Kratos Admin API URL used for identity provisioning and management |
| `BACKEND_KRATOS_SESSION_COOKIE` | `ory_kratos_session` | The sole browser cookie forwarded to Kratos `whoami` |
| `BACKEND_KRATOS_PUBLIC_TIMEOUT` | `2.0` | Public API timeout in seconds |
| `BACKEND_KRATOS_ADMIN_TIMEOUT` | `10.0` | Admin API timeout in seconds |
| `BACKEND_KRATOS_PUBLIC_CONCURRENCY` | `20` | Maximum concurrent Public API calls |
| `BACKEND_KRATOS_ADMIN_CONCURRENCY` | `4` | Maximum concurrent Admin API calls |
| `BACKEND_KRATOS_RECONCILE_INTERVAL` | `300` | Identity projection reconciliation interval in seconds |
| `BACKEND_BOOTSTRAP_ADMIN_LOGIN` | `admin` | Lowercase login for the first administrator |
| `BACKEND_BOOTSTRAP_ADMIN_NAME` | `Администратор` | Display name for the first administrator |
| `BACKEND_BOOTSTRAP_ADMIN_PASSWORD` | empty | Development-only initial password; use this or `*_PASSWORD_FILE`, never both |
| `BACKEND_BOOTSTRAP_ADMIN_PASSWORD_FILE` | empty | Path to the file containing the initial password; recommended for production |

Database settings are documented in [database.md](database.md#configuration).
Redis settings are documented in [redis.md](redis.md#configuration).

## CORS origins

`BACKEND_CORS_ORIGINS` accepts one format: a JSON array of HTTP or HTTPS origins.
Each origin consists of a scheme, hostname, and optional port. Paths, credentials,
query strings, and fragments are rejected.

```env
BACKEND_CORS_ORIGINS='["https://app.example.com","https://admin.example.com"]'
```

For a local frontend with an explicit port:

```env
BACKEND_CORS_ORIGINS='["http://localhost:5173"]'
```

Use an empty JSON array when cross-origin browser access is not needed:

```env
BACKEND_CORS_ORIGINS='[]'
```

Wrap the JSON array in single quotes so dotenv loaders preserve the double quotes around each origin.

## First administrator

The prestart container creates one active `administrator` only while the local
`users` table is empty. It uses the same user-management service as the API and
records the operation in the audit log. Later starts are no-ops.

Set exactly one password source before the first start. A password must contain
at least 12 characters. Prefer a mounted secret file in production:

```env
BACKEND_BOOTSTRAP_ADMIN_LOGIN=admin
BACKEND_BOOTSTRAP_ADMIN_NAME=Администратор
BACKEND_BOOTSTRAP_ADMIN_PASSWORD_FILE=/run/secrets/bootstrap_admin_password
```

For local development only, `BACKEND_BOOTSTRAP_ADMIN_PASSWORD` can be used
instead. The password is never logged. If provisioning is interrupted, the
next prestart resumes the backend-owned bootstrap identity.
