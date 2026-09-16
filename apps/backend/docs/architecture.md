# Backend architecture

The backend is a modular monolith. This document describes the state the code
is actually in, plus the known debt and the order in which it is being paid.

## Modules

A module is a **consistency boundary**: the set of tables that change inside
one transaction. It is not "a thing from the problem domain". There are five.

```text
production   batches, receipts, shipments, preparation, KG, production orders
quality      verification, defects, quality-check catalogue
equipment    PAK devices, credentials, machine authentication
identity     users, provisioning, bootstrap, reconciliation
audit        audit events, actor/entity vocabulary, transactional writer
```

Supporting packages are not modules: `app.shared` (security kernel, unit of
work), `app.core` (settings, logging, error taxonomy), `app.components`
(dependency-free key generation), `app.infrastructure` (database, Redis,
Kratos, Hydra adapters), `app.api`, `app.bootstrap`, `app.middleware`,
`app.realtime`, `app.worker`, `app.platform`.

### What is not a boundary

The sub-packages inside `app/domains/production` and `app/domains/quality` are
**file organisation, not boundaries**. `CreateBatch` writes `Batch`, allocates
`KgUnit` rows and creates the preparation job in a single transaction, so a
port between them would be a lie. Inside one module, direct imports of a
sibling's `model`, `repository`, `queries`, `commands` and `rules` are correct.

Consequently `app/domains/production/exceptions.py` is the production module's
error vocabulary, not a misplaced file. Names in it still say `Batch*` for
receipt and shipment errors; that is a naming debt, not a layering one.

## Cross-module ports

Only traffic that crosses a module boundary goes through a Protocol. The
consumer declares the port; the provider implements it; the composition root
wires them.

| Port | Declared by | Implemented by |
|---|---|---|
| `VerificationHistoryPort` | `production/contracts.py` | `quality/verification/adapters.py::VerificationHistoryProvider` |
| `VerificationKgPort` | `quality/verification/contracts.py` | `production/adapters.py::ProductionVerificationKgAdapter` |
| `VerificationPakPort` | `quality/verification/contracts.py` | `equipment/pak/adapters/verification.py::adapt_pak` |
| `PakVerificationHistoryPort` | `equipment/pak/contracts.py` | `quality/verification/adapters.py::QualityPakVerificationHistoryAdapter` |
| `UserIdentityProviderPort` | `identity/users/contracts.py` | `infrastructure/kratos/users.py` |
| `PakOAuthClientPort`, `PakTokenIntrospectorPort` | `equipment/pak/contracts.py` | `infrastructure/hydra/` |
| `WorkDispatcher` | `production/preparation/dispatcher.py` | `worker/preparation_dispatcher.py` (declared but bypassed, see debt) |

A module declares its full outbound surface in one file: `contracts.py` at the
module root. `adapters.py` at the module root holds the implementations that
module provides to others.

## Composition and startup

`app.bootstrap.application.ApplicationComponents` owns only process-lifetime
infrastructure: database, Redis, Kratos/Hydra clients and machine
authentication. It does not retain business commands or service facades.

Permission composition is explicit in `app.main.create_app`:

```text
compose_permission_registry()
  -> install_permission_registry(registry)
```

`app.shared.security` is intentionally independent of bootstrap and feature
modules. Importing it provides an empty registry until the composition root
installs the application registry. `app.bootstrap.permissions` is the only
module that knows the complete permission surface.

HTTP routers consume `app.shared.security.dependencies` for a current
principal and permission checks. `app.api.auth_deps.get_current_principal`
contains the concrete cookie/Kratos/local-user implementation; `create_app`
binds that implementation to the shared dependency contract for each FastAPI
application instance.

Lifespan constructs and invokes startup workflows directly. User reconciliation
and stale-verification reconciliation are not stored in `app.state`.

## Presentation

HTTP adapters construct commands, queries, repositories and a transaction
boundary locally. A request adapter may obtain long-lived infrastructure from
`request.app.state` (database/session factory, settings, Kratos/Hydra clients
or adapter factories), but it does not obtain a business command or
`*ManagementService` from application state.

## Transactions

`app.shared.uow.transaction` is the only transaction boundary. It owns the
session lifecycle and `session.begin()`, nothing else. Repositories, commands
and audit writers receive the yielded session and never commit or roll back.

Read paths open a session without `begin()`. Long-running work (preparation)
uses many short committed transactions with row locks rather than one long
transaction. Post-commit side effects are dispatched after the `async with`
block closes.

## Audit ownership

Audit is canonically owned by `app.audit`: its `AuditEvent` mapped model, typed
actor/entity vocabulary, repository, HTTP schemas/router, permission and
`TransactionalAuditWriter` live there. The writer appends within the caller's
transaction and does not own commit or rollback.

## Residual debt

Ordered by the wave that pays it. Nothing here is mechanically enforced yet,
which is itself the last item.

### Wave 2 - composition

* `_session_factory` is copy-pasted into eight routers and `_transaction` into
  three, each with a `cast` over untyped `request.app.state`.
* Commands are assembled by hand in every handler. A `Command.build(session)`
  classmethod would remove the duplication without introducing a container or
  returning to service facades.
* Post-commit effects are registered as semantic values through
  `uow.after_commit(effect)`. The in-process executor is bound to Celery and
  Redis only in composition; it can later be replaced with an outbox writer
  without changing command code.

Note: the transaction boundary must stay in the handler body. FastAPI runs the
exit code of `yield` dependencies **after** the response is produced, so
committing inside a dependency would send `201` before the commit could fail.

### Wave 3 - cross-module data coupling

* `quality/verification/repository.py` imports `production.kg.model.KgUnit` and
  queries a production table directly, defeating `VerificationKgPort`, which
  exists for exactly this.
* `production/kg/repository.py` embeds `latest_verification_projection`, a
  quality-owned subquery, in its own SELECTs. Needs a read port.
* Cross-module ORM relationships: `identity.users.model.User` is imported by
  the batches, receipts and shipments models purely to render an author name.
  `app.audit` already solves this by snapshotting `actor_display_name`; the
  same denormalisation would remove three cross-module relationships and three
  `selectinload` calls from list endpoints.
* `quality/verification/model.py` imports `PakDevice` at runtime for a
  relationship; `production/kg/model.py` already guards its equivalent with
  `TYPE_CHECKING`.

### Wave 4 - correctness and enforcement

* `ForbiddenError` and `IdentityNotFoundError` are each defined twice, in
  `shared/security/exceptions.py` and `auth/exceptions.py`, with identical wire
  codes but different classes. `except` catches different things depending on
  the import path. Keep the `shared/security` definitions.
* `app/auth/router.py` is an HTTP adapter inside a contracts package; it drags
  `app.api` and `app.domains` into anything that imports `app.auth`. Move it to
  `app/api/`.
* `app/auth/principal.py`, `roles.py` and `permissions.py` are empty
  re-export shims with no domain consumers. Delete after rewriting the few
  remaining imports.
* `equipment/pak/router.py` mounts `quality.checks.router`, performing URL
  composition for another module and creating an import cycle. Move to
  `app/api/main.py`.
* `quality/checks/router.py` guards a quality endpoint with `PakPermission`, and
  `quality/verification/router.py` consumes `equipment/pak/deps.CurrentPakDep`.
* The permission registry is a process-global mutable singleton. Reading it
  before installation silently yields an empty frozenset. Fail loudly instead.
* `reconcile_forever` and `verification_sweeper_forever` run in every API
  replica with no advisory lock, duplicating work when scaled horizontally.
* No `import-linter`/`tach` contract exists, so none of the above is enforced.
  Add it last, pinning the achieved state and listing the remainder as explicit
  exceptions.

### Test suite debt

* `tests/api` is documented as "external dependencies mocked" but several
  modules open real Postgres connections, so the default suite cannot run
  without a database.
* `mypy` is clean over `app` and reports 137 errors over `tests` and `tools`.
* `tests/unit` layout has diverged from the code: both `unit/pak` and
  `unit/equipment/pak`, both `unit/users` and `unit/identity/users`, both
  `unit/batch` and `unit/production` exist.

## Out of scope

Paying this debt does not change API payloads/paths, authentication protocol,
Kratos/Hydra behavior, Alembic or database schema, verification locking,
worker/preparation semantics, Redis/SSE, or key generation. Waves that need a
schema change (the `User` denormalisation) must follow expand-and-contract.
