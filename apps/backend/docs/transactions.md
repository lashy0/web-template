# Transactions and external systems

A request changes data in one database transaction owned by a unit of work
(`app.lib.uow`). The change and its audit entry commit together, and a failed
commit reaches the client as an error instead of a silent success.

## Rules

- **Services never commit or roll back.** They write through their session and
  at most `flush()`. The unit of work commits.
- **Handlers that change data request `uow`.** The app-level `uow` dependency
  commits after the handler returns and **before** the response is sent
  (Litestar runs the code after a dependency's `yield` at that point and throws
  handler exceptions into it). A commit failure becomes an error response; a
  handler exception rolls everything back, including audit entries.
- **Request `uow` even when the service does not take it.** Litestar resolves a
  dependency only for handlers that declare it; without the parameter nothing
  commits. Mark such a parameter `# noqa: ARG002 - requested so the change commits`.
- **Write audit entries in the same request.** `AuditLogService` shares the
  request session, so the entry commits or rolls back with the change.
- **Outside HTTP** (CLI, jobs, tests) use the same boundary explicitly:

  ```python
  async with unit_of_work(session) as uow:
      await users_service.create_user(data, kratos=kratos, uow=uow)
  ```

## Commit errors

| Failure at commit | Raised by `UnitOfWork.commit` | Response |
|---|---|---|
| constraint violation (`sqlalchemy.exc.IntegrityError`) | `IntegrityError` | 409, fixed detail |
| anything else: lost connection, serialization failure, deadlock | `RepositoryError` | 500, logged |

Details are fixed so SQL never reaches the client. Constraint violations
normally surface earlier, at `flush` inside a repository, with the service's
domain-specific messages; the commit mapping is a safety net.

Litestar finishes `yield` dependencies in an `anyio` task group when a handler
has more than one of them, and Advanced Alchemy service providers are
generators too. A commit error therefore reaches the application as an
`ExceptionGroup`. `exception_group_to_http_response` (registered in
`ApplicationCore`) unwraps a single error and dispatches it to the handler that
would have handled it directly; several errors become a logged 500.

## External systems

Kratos and Hydra cannot join the transaction. Access requires both the external
state and the local row (see `docs/authentication.md`), so effects are ordered
so that any partial failure leaves access **closed**:

| Effect | Examples | Where | On failure |
|---|---|---|---|
| Grants access | create identity or Hydra client, activate, change login | inline, before the commit | the request fails; nothing is committed |
| Revokes access that a local row also guards | deactivate, archive, delete, revoke tokens | `uow.after_commit(...)` | logged; the committed row already denies access |
| Cleans up a resource created before a failed commit | delete the new identity or client, restore the old login | `uow.on_rollback(...)` | logged; the leftover grants nothing without a local row |

Registered effects never change the outcome of the request. Operations are
idempotent towards the external system, so repeating a request repairs an
earlier failed effect.

Two exceptions:

- **Password change.** No local state closes access, so revoking the sessions
  runs inline and its failure is reported.
- **PAK secret rotation.** Hydra owns the secret and the database stores its
  encrypted copy, so no ordering is safe: the previous secret is restored in
  Hydra through `uow.on_rollback(...)`.

## Session lifecycle

Every data-changing handler requests `uow`; nothing commits implicitly. The
SQLAlchemy plugin uses Advanced Alchemy's default `before_send_handler`, which
only closes the session. A handler that writes without requesting `uow`
therefore loses its writes.
