# Background tasks

Background work runs on [SAQ](https://github.com/tobymao/saq) through
`litestar-saq`, with Redis as the broker. The plugin is built in
`app/server/plugins.py` (`create_task_queue`); task functions are listed there
by dotted path in `TASKS`, and recurring ones as `CronJob`s.

## Tasks

| Task | When | What |
|---|---|---|
| `app.domain.quality.tasks.expire_stale_verification_sessions` | every minute | closes verification sessions idle past `BACKEND_VERIFICATION_SESSION_TTL_MINUTES` as incomplete; see [verification](domain/verification.md) |

A task receives the SAQ context filled by `app/lib/worker.py`: the settings and
a database config whose engine lives as long as the worker process. It opens
its own sessions and commits through `unit_of_work`.

## Where workers run

| Environment | How | Setting |
|---|---|---|
| deployment | a `worker` service of its own: `app workers run` | `BACKEND_WORKERS_IN_SERVER` unset (false) |
| development | child processes of `litestar run` | `BACKEND_WORKERS_IN_SERVER=true` |
| tests | none; tests call task functions directly | set false in `tests/conftest.py` |

In a deployment the worker is separate from the API so that:

- the number of workers does not grow with API processes or replicas;
- deploying the API does not interrupt running jobs, and the worker gets its
  own shutdown grace period;
- a heavy job uses the worker container's CPU and memory limits, and a crash
  on either side leaves the other running.

The API only enqueues jobs. It connects to Redis on the first enqueue, not at
startup.

## Redis keys and permissions

The queue is named after `BACKEND_REDIS_PREFIX` (`otk-app`), so SAQ keeps its
keys under `saq:otk-app:*` and `saq:job:otk-app:*`; job abort markers go to
`saq:abort:*` without the queue name. The runtime ACL user `otk_app_runtime`
(`infrastructure/database/redis/users.acl.template`) may use only these keys,
the `otk-app:*` namespace, and the commands SAQ needs. When a SAQ upgrade or a
new feature is denied by Redis (`NOPERM`), check `ACL LOG` as the admin user
and extend the template.

The production `volatile-ttl` eviction policy is safe for the queue: only
finished jobs and short locks carry a TTL; waiting jobs and the queue
structures have none and are never evicted.
