# Realtime events

The browser learns that something changed from a stream of server-sent events,
`GET /events`, and then reads the new state through the usual routes. The
delivery is Litestar's `ChannelsPlugin`, wrapped in `app/lib/realtime.py`; each
domain declares its events in `app/domain/<domain>/events.py`.

## Events are signals

An event says **what changed**, not the new state:

```text
event: verification.changed
data: {"pakId":"0199..."}
```

Events are not stored. One published while nobody listens is lost, and so is
one published while Redis is down. That is safe because the client treats the
stream as a hint to reread, never as the data:

- the stream opens with a `resync` event, and the client rereads everything it
  shows in realtime;
- `resync` is sent again when a client read too slowly and its backlog of 256
  events was dropped.

Events lost while an API process was cut off from Redis are **not** announced:
a page catches up with the next event about what it shows, or when its stream
reconnects (at most 15 minutes later). The PAK slots are also reread every
minute.

| Event | Data | Permission | Published when |
|---|---|---|---|
| `resync` | `{}` | none | the stream opens; events may have been lost |
| `verification.changed` | `pakId`, `batchId` | `verification.read` | a session of the PAK on a unit of the batch started, advanced or ended; see [verification](domain/verification.md) |
| `pak_check.changed` | `checkId` | `verification.read` | a PAK reported a check for the first time or another defect group code for it |
| `batch.changed` | `batchId` | `batches.read` | the batch, its receipts or shipments, or the state of its KG units changed; see [batches](domain/batches.md) |
| `user.changed` | `userId` | `users.read` | a user was created, changed (including the own profile), activated, archived or deleted through the API; the `otk users` commands announce nothing |
| `pak.changed` | `pakId` | `paks.read` | a PAK was created, changed, activated, archived or deleted, or its access key was rotated; its reports announce `verification.changed` instead |
| `kg_prefix.changed` | `prefixId` | `kg_prefixes.read` | a KG prefix was created, changed, archived or deleted |
| `kg_version.changed` | `versionId` | `kg_versions.read` | a KG version was created, changed, archived or deleted |
| `multicast_group.changed` | `multicastGroupId` | `multicast_groups.read` | a multicast group was created, changed, archived or deleted |
| `production_order.changed` | `orderId` | `production_orders.read` | a production order was created, changed, archived or deleted |
| `defect_group.changed` | `groupId` | `defects.read` | a defect group was created, changed, archived or deleted |
| `defect_type.changed` | `typeId` | `defects.read` | a defect type was created, changed, archived or deleted |

An event about a record is published by the route that changes it, together
with its audit entry, through `changes.record(..., event=...)` (see
[audit](audit.md)); a change without an audit entry, such as adding units to a
shipment, uses `changes.announce(event)`. The
frontend maps each event to the queries to reread in `src/app/live-updates.ts`.

## Declaring and publishing an event

An event is a `RealtimeEvent` with a type and the permission a user needs to
receive it:

```python
class VerificationChanged(RealtimeEvent):
    event_type: ClassVar[str] = "verification.changed"
    permission: ClassVar[str] = VerificationPermission.READ

    pak_id: UUID
    batch_id: UUID
```

Publish it **after the commit**, through the unit of work, so a client that
rereads on the event sees the change:

```python
announce_after_commit(uow, realtime, event)
```

A failed publish is logged and does not fail the request, like every
post-commit effect (see [transactions](transactions.md)). User routes and the
PAK machine API publish through `changes`; a background task takes `realtime`
from the worker context (`ctx["realtime"]`). `verification_change_events`
builds one event per PAK and batch for both machine requests and the worker.

Put only identifiers in an event. Every user who holds the permission receives
it, whatever records they may read.

## The stream

`GET /events` needs a browser session, like any other route. Every signed-in
user may open it; the stream subscribes to the channels of the permissions the
user had when it opened.

- A comment (`: ping`) is sent every 20 seconds of silence, so proxies keep the
  connection and a closed one is noticed.
- The stream ends after 15 minutes and the browser reconnects (`retry: 2000`).
  The reconnect goes through authentication again, so an ended session or a
  changed role takes effect within that time. Until then a user keeps
  receiving signals, which is why they carry no data.
- The stream holds no database connection.

## Delivery between processes

PAK reports arrive at any API process and the sweep of stale sessions runs in
the worker, while a browser is connected to one API process. Events therefore
go through Redis pub/sub, with Litestar's `ChannelsPlugin`:

- Every permission has a channel, `<BACKEND_REDIS_PREFIX>:events:<permission>`
  (`otk-app:events:batches.read`), which the runtime ACL user may use
  (`&otk-app:*`). An event goes to the channel of its permission.
- The application runs the plugin in its lifespan; the worker starts it in
  `app/lib/worker.py`. A process subscribes to a channel in Redis while one of
  its streams needs it, over one connection for all of them.
- When that connection fails, the process listens again after a growing delay
  (1 to 30 seconds); redis-py then reconnects and subscribes anew. What was
  published in between is lost, without a `resync`.
- Publishing uses a 2-second timeout and no retries: it is part of a request
  and must not hold the response while Redis is down.

`BACKEND_REALTIME_BACKEND=memory` keeps events inside one process instead of
Redis. It is for tests (`tests/conftest.py`); a deployment needs `redis`, the
default.
