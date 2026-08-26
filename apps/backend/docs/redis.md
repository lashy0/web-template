# Redis

The backend uses the asynchronous client provided by `redis-py`. One client is
created for each application worker during the FastAPI lifespan and is closed
on application shutdown. The client owns a connection pool and can be shared
between concurrent requests handled by the same worker.

## Using Redis

Inject `RedisDep` into an endpoint or another FastAPI dependency:

```python
from app.api.deps import RedisDep


async def get_value(
    redis: RedisDep,
) -> str | None:
    return await redis.get("example:key")
```

Feature modules should own their key format, serialization, TTLs, and
invalidation rules. Avoid spreading raw key strings across routers and
services.

## Configuration

The connection is configured with the following environment variables:

| Variable | Default | Description |
| --- | --- | --- |
| `BACKEND_REDIS_URL` | empty | Complete connection URL; overrides the individual connection fields |
| `BACKEND_REDIS_HOST` | `localhost` | Redis server hostname |
| `BACKEND_REDIS_PORT` | `6379` | Redis server port |
| `BACKEND_REDIS_PASSWORD` | empty | Redis password |
| `BACKEND_REDIS_DB` | `0` | Logical Redis database |
| `BACKEND_REDIS_PREFIX` | `web-app` | Prefix prepended to application-owned Redis keys |
| `BACKEND_REDIS_MAX_CONNECTIONS` | `20` | Maximum pool size per application worker |
| `BACKEND_REDIS_SOCKET_CONNECT_TIMEOUT` | `2` | Connection timeout in seconds |
| `BACKEND_REDIS_SOCKET_TIMEOUT` | `2` | Command timeout in seconds |
| `BACKEND_REDIS_HEALTH_CHECK_INTERVAL` | `30` | Connection health check interval in seconds |

Each application worker has its own Redis connection pool. Calculate the maximum
number of application connections as:

```text
replicas * workers * REDIS_MAX_CONNECTIONS
```

For example, one backend replica with four workers and the default settings can
open up to 80 Redis connections. Connections are opened as needed.

Keep this number below the Redis server or provider limit. Leave some connections
for monitoring, administrative commands, background jobs, and other clients. If
all connections in a worker pool are busy, Redis operations can fail.

For local compatibility, `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`,
`REDIS_RUNTIME_PASSWORD`, and `REDIS_DB` are accepted as fallbacks. Component
fields always use the fixed `web_app_runtime` ACL user.
When both forms are set, the `BACKEND_REDIS_*` variable takes precedence.

Use `BACKEND_REDIS_URL` for managed Redis or TLS connections:

```env
BACKEND_REDIS_URL=rediss://user:password@redis.example.com:6380/0
```

When `BACKEND_REDIS_URL` is set, `BACKEND_REDIS_HOST`, `BACKEND_REDIS_PORT`,
`BACKEND_REDIS_PASSWORD`, and `BACKEND_REDIS_DB` are ignored.

Build application-owned keys with `build_redis_key()` so the configured prefix
and key format remain consistent between reads, writes, and invalidation.

Every session write must set a TTL. The runtime ACL is restricted to
`web-app:*` and the small command set needed by TTL-backed sessions. It excludes
flush, configuration, scripting, Pub/Sub, and all other keys.

The client explicitly uses RESP2 so its connection setup stays within the
documented `PING` and `CLIENT SETINFO` ACL permissions.

```python
from redis.asyncio import Redis

from app.core.config import Settings
from app.infrastructure.redis.keys import build_redis_key


class ExampleCache:
    def __init__(
        self,
        redis: Redis,
        settings: Settings,
    ) -> None:
        self.redis = redis
        self.settings = settings

    async def get(self, item_id: int) -> str | None:
        key = build_redis_key(
            self.settings,
            "items",
            item_id,
        )
        return await self.redis.get(key)
```

## Testing

API tests mock Redis and Postgres readiness checks and use the `api` marker.
The `integration` marker is reserved for tests that connect to real services.
Integration tests are excluded from the default test run.

With the required external services available, run the integration suite from
`apps/backend/`:

```console
uv run --env-file ../../.env pytest -m integration
```
