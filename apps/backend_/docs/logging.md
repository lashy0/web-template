# Logging

The backend logs through [structlog](https://www.structlog.org/) with
Litestar's `StructlogPlugin`, as litestar-fullstack does. Records of the
application and of the libraries it uses (Litestar, SQLAlchemy, SAQ, uvicorn,
httpx) share one format and go to stdout. The setup lives in
`app/server/plugins.py` (`create_logging`) and `app/lib/log.py`.

## Format

- **In a terminal**: one readable line per record, with colors and rich
  tracebacks. Columns are the UTC time (`HH:MM:SS`), the level, the source
  (`app` for the backend's own events, otherwise the library's package, such
  as `uvicorn`, `sqlalchemy`, `autowire`), the event and its fields. A request
  line puts the fixed-width columns first: method, status (green 2xx, cyan
  3xx, yellow 4xx, red 5xx), duration, then the path and the first 8
  characters of the request ID, so a long path shifts nothing:

  ```
  14:34:46 INFO  uvicorn    Application startup complete.
  14:34:46 INFO  http       GET     401  3.1ms  /auth/me                                 f862631b
  14:34:46 INFO  http       POST    201   45ms  /batches                                 0c9e1a22
  14:34:46 ERROR http       PATCH   500  1.24s  /packing/units/a1b2c3d4e5000001/pack     77ab01fe
  14:34:46 WARN  app        pak_check.unknown_defect_group pak_code=pak-1 request_id=250a8c33
  ```

- **Without a terminal** (containers, CI, a file): one JSON object per line
  with `event`, `level`, `timestamp` (ISO 8601 in UTC) and the event's full
  fields. Records from standard `logging` add `logger`.
- `BACKEND_LOG_JSON=true` forces JSON in a terminal too.

A value JSON cannot represent is written with `repr()`; logging never fails
the call that logs.

## Writing a log entry

The event name is the message; everything else is a field:

```python
import structlog

logger = structlog.get_logger()

logger.warning("pak_check.unknown_defect_group", pak_code=pak.code, defect_group_code=code)
logger.exception("uow.rollback_failed")  # inside ``except``: adds the traceback
```

- Name events `<subject>.<what_happened>` in `snake_case`, like error codes.
  Put variable data in fields, not in the event name.
- Never log secrets, tokens, passwords or personal data beyond IDs and logins.
- Client errors (4xx) are not logged: the response already tells the client,
  and the request line records the status.

## Requests

`RequestContextMiddleware` gives every HTTP request an ID and binds it to the
structlog context, so every application record of the request carries
`request_id`. The ID is taken from an incoming `X-Request-ID` header when a
proxy set a well-formed one, otherwise generated, and returned in the
`X-Request-ID` response header.

`log_request`, a `before_send` hook, writes one `http.request` line when the
response is sent: `method`, `path`, `status_code`, `duration_ms`. Its level is
`error` for 5xx and `info` otherwise. It is a hook, not part of the
middleware, because errors raised by middleware (401 from authentication)
become responses outside every middleware; every response passes the hook.
Headers, cookies and bodies are not logged. Successful requests that say
nothing of their own are logged at `debug`: `/health`, polled by
orchestrators every few seconds, the API docs under `/schema`, and CORS
preflights (`OPTIONS`). A failing one is logged like any other request.
Requests matching no route are not logged. uvicorn's access log is lowered to
warnings, since the request line replaces it.

Records from standard `logging` are rendered on Litestar's queue listener
thread and carry no `request_id`.

## Errors

| Error | Logged by | Event |
|---|---|---|
| application or repository error mapped to 5xx | `exception_to_http_response` | `http.server_error` |
| any other exception, or an HTTP exception with a 5xx status | `log_unhandled_exception` | `http.unhandled_exception` |
| failed rollback or effect around a commit | `UnitOfWork` | `uow.rollback_failed`, `uow.after_commit_effect_failed`, `uow.rollback_effect_failed` |

Both error events include the traceback; see [errors](errors.md) and
[transactions](transactions.md).

## Settings

| Variable | Default | Meaning |
|---|---|---|
| `BACKEND_LOG_LEVEL` | `INFO` | lowest level of the application and of libraries without a level of their own |
| `BACKEND_LOG_JSON` | `false` | JSON even in a terminal |
| `BACKEND_LOG_SQLALCHEMY_LEVEL` | `WARNING` | `INFO` writes every SQL statement |
| `BACKEND_LOG_SAQ_LEVEL` | `WARNING` | `INFO` writes every job, including the scheduled ones each minute |

httpx and httpcore log at least at `WARNING`, so request lines of the Kratos
and Hydra clients stay out of the log.

Loggers are not cached (`cache_logger_on_first_use=False`), so an application
built later, as tests do, reconfigures loggers that modules already use.
