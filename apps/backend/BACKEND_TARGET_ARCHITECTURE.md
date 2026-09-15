# Backend architecture

The backend is a modular monolith. Business ownership is in `app.contexts`:

```text
production: batches, receipts, shipments, preparation, KG, production orders
quality: verification, defects, PAK test catalogue
equipment: PAK devices, credentials and machine authentication
identity: users, provisioning, bootstrap and reconciliation
shared.security: roles, principal, identity contracts and registry API
```

HTTP adapters construct commands, queries, repositories and a transaction
boundary locally. A request adapter may obtain long-lived infrastructure from
`request.app.state` (database/session factory, settings, Kratos/Hydra clients
or adapter factories), but it does not obtain a business command or
`*ManagementService` from application state.

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
contexts. Importing it provides an empty registry until the composition root
installs the application registry. `app.auth.permissions` is a compatibility
view of the canonical shared-security API only; it has no bootstrap import and
cannot trigger registry construction.

Lifespan constructs and invokes startup workflows directly. User reconciliation
and stale-verification reconciliation are not stored in `app.state`.

## Production presentation

`/batches`, receipts and shipments are production adapters. They invoke
`CreateBatch`, `UpdateBatch`, `CompleteBatch`, `SetBatchArchived`,
`AssignProductionOrder`, `DeleteBatch`, `RetryPreparation`, receipt commands,
shipment commands and their queries directly. The API paths, schemas, status
codes, permission checks, database schema and documented document/KG semantics
remain unchanged.

Production orders expose commands, queries, repository and rules directly;
there is no production-order service facade.

## Legacy audit boundary

Business `app.modules` packages have been removed. Canonical contexts are the
sole owner of mapped models, schemas, permissions, exceptions and business
logic. `app.modules.audit` is the only remaining legacy module because its
mapped audit model and typed actor/entity vocabulary are still in use.

The one intentional context-to-legacy dependency is
`app.modules.audit.types`. Audit migration is deliberately out of scope: its
typed actor/entity vocabulary remains the shared transactional audit boundary.
Feature-specific business logic does not remain in that dependency.

## Out of scope

This state does not change API payloads/paths, authentication protocol,
Kratos/Hydra behavior, Alembic or database schema, verification locking,
worker/preparation semantics, Redis/SSE, key generation, or audit ownership.
Audit relocation remains an optional, separate small migration.
