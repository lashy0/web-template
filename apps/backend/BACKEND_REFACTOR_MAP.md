# Backend refactor map

Snapshot of `app/` before refactoring.  No application code was changed.  The
default `BACKEND_API_PREFIX` is empty, so paths below are shown without a
prefix (deployments may prepend that setting).

## Composition

| Area | HTTP/router | Models / repositories | Service entry points |
| --- | --- | --- | --- |
| `auth` | `/auth/me` | none; session lookup reads `users` | Kratos session verification, principal and role/permission matrix |
| `users` | `/users` | `User`; `UserRepository` | `UserManagementService` -> account, provisioning, bootstrap, reconciliation |
| `audit` | `/audit` | `AuditEvent`; `AuditRepository` | `AuditService` |
| `pak` | `/pak` | `PakDevice`, `PakTest`; `PakRepository`, `PakTestRepository` | device, provisioning, credentials, authentication, catalog |
| `defects` | `/defects` | `DefectGroup`, `DefectType`; group/type repositories | `DefectManagementService` -> group/type |
| `kg` | `/kg` | `KgUnit`, `KgDevEuiPrefix`, `KgVersion`, `LoRaWanCredentials`; unit/prefix/version/credentials repositories | unit, prefix, version, credentials |
| `batch` | `/batches` | `Batch`, `BatchKeyGenerationJob`, `BatchLoRaWanConfig`, receipt/shipment/item; batch/receipt/shipment repositories | `BatchManagementService` -> batch, receipt, shipment; key-generation job |
| `production_order` | `/production-orders` | `ProductionOrder`; `ProductionOrderRepository` | `ProductionOrderManagementService` -> order |
| `verification` | `/verification` | `VerificationSession`, `VerificationStep`; session/step repositories | management -> session, step, cleanup |
| `lorawan` | none | persistence is `kg.LoRaWanCredentials` | DevEUI normalization, deterministic credential generator, AES-GCM serializer/cipher |

Shared infrastructure: async SQLAlchemy/Postgres, Redis, Kratos (identities),
Hydra (PAK OAuth clients), Celery, and a separate SSE realtime FastAPI app.
`app/main.py` constructs the management services and exposes them through
`app.state`; facade services own request transaction/session boundaries.

## Direct module dependency map

Arrows mean a direct import or operational use, not merely a common API
composition dependency.

```text
auth ───────────────> batch, defects, kg, pak, production_order, users, verification
users ──────────────> audit; auth (roles/contracts); Kratos
pak ────────────────> audit, defects; Hydra; auth token contracts
defects ────────────> audit
kg ─────────────────> audit, batch (prefix/version usage), verification; lorawan credentials
batch ──────────────> audit, kg, production_order, verification, lorawan; worker; Redis/realtime
production_order ──> audit, batch
verification ──────> kg, pak (including test catalogue)
lorawan ───────────> standalone domain/crypto utility; called by batch key generation
audit ─────────────> standalone append-only snapshot store
```

Model-level links are deliberately stronger in a few places: `Batch` imports
KG/version/order/user models; verification imports PAK and references KG;
`PakTest` references defect groups. `auth/permissions.py` is the central
cross-feature permission union. `app/api/main.py` only composes routers.

## Public HTTP surface

All management routes use the Kratos-cookie principal plus a feature
permission. Machine verification routes use a Hydra bearer token resolved to
an active, unarchived PAK.

| Area | Endpoints (method + path pattern) |
| --- | --- |
| health | `GET /health/live`, `GET /health/ready` |
| auth/audit | `GET /auth/me`; `GET /audit` |
| users | `GET, POST /users`; `GET, PATCH, DELETE /users/{id}`; `PUT /users/{id}/{password,active,archived}` |
| PAK | `GET, POST /pak`; `GET /pak/tests`, `GET /pak/tests/{id}`; `GET, PATCH, DELETE /pak/{id}`; `GET /pak/{id}/access-key`; `POST /pak/{id}/access-key/rotate`; `PUT /pak/{id}/{active,archived}` |
| KG | `GET, POST /kg/dev-eui-prefixes`; `PATCH, DELETE /kg/dev-eui-prefixes/{prefix}`; `PUT /kg/dev-eui-prefixes/{prefix}/archived`; same CRUD/archive set for `/kg/versions`; `GET /kg`, `GET /kg/{dev_eui}`, `GET /kg/batch/{batch_id}` |
| batches | `GET /batches/`, `POST /batches`, `GET, PATCH, DELETE /batches/{id}`; `GET /batches/dev-eui-range-preview`; `PUT /batches/{id}/{archived,production-order}`; `POST /batches/{id}/{complete,preparation/retry}` |
| receipts | `GET, POST /batches/{id}/receipts`; `PATCH /batches/{id}/receipts/{receipt_id}`; `POST /batches/{id}/receipts/{receipt_id}/void` |
| shipments | `GET, POST /batches/{id}/shipments`; `PATCH /batches/{id}/shipments/{shipment_id}`; `GET, POST /batches/{id}/shipments/{shipment_id}/items`; `DELETE .../items/{dev_eui}`; `POST .../{complete,void}` |
| production orders | `GET /production-orders/`, `POST /production-orders`; `GET, PATCH, DELETE /production-orders/{id}`; `PUT /production-orders/{id}/archived` |
| verification | operator: `GET /verification/sessions`, `GET /verification/sessions/{id}`; machine: `POST /verification/sessions`, `POST /verification/sessions/{id}/steps`, `PUT /verification/sessions/{id}/steps/{step_no}`, `POST /verification/sessions/{id}/complete` |
| defects | groups and types each: `GET, POST /defects/{groups,types}`; `GET, PATCH, DELETE /defects/{groups,types}/{id}`; `PUT .../{id}/archived` |

The standalone realtime app, not included by `app/api/main.py`, exposes
`GET /health` and unauthenticated SSE `GET /events`.

## Tables and material foreign keys

* `users`; `audit_events` has no FK by design: it stores actor/entity
  identifiers and old/new JSONB snapshots so history survives deletion.
* `defect_groups` -> `defect_types.group_id` (`RESTRICT`); `pak_tests.defect_group_id`
  -> groups (`RESTRICT`).
* `pak_devices`; verification sessions reference it with `RESTRICT`.
* `kg_dev_eui_prefixes`, `kg_versions`; `batches.dev_eui_prefix` and optional
  `batches.kg_version_id` reference them. `kg_units.batch_id -> batches`.
* `production_orders`; optional `batches.production_order_id -> production_orders`
  is `RESTRICT`. `batches.created_by_user_id`, receipt/shipment creator IDs
  point to `users` with `SET NULL`.
* `batches` owns (`CASCADE`) one `batch_key_generation_jobs` row and one
  `batch_lorawan_configs` row. Receipts and shipments reference batch;
  `batch_shipment_items` is the `(shipment_id, kg_dev_eui)` link to shipment
  and KG.
* `lorawan_credentials.kg_dev_eui -> kg_units.dev_eui` (`CASCADE`), one-to-one.
* `verification_sessions.kg_dev_eui -> kg_units` and `.pak_id -> pak_devices`
  are `RESTRICT`; steps cascade from session and reference `pak_tests` and
  `defect_groups` with `RESTRICT`.

Notable DB invariants: positive batch quantities/receipt quantities and
verification slot/step counts; canonical lowercase DevEUI/prefix formats;
unique codes/identities; one `RUNNING` verification per KG and per PAK slot;
unique step number per session. `BatchKeyGenerationJob` is omitted from the
registry's named exports, but importing `app.modules.batch.models` still
registers it in SQLAlchemy metadata.

## Non-HTTP execution and side effects

* On API startup, `main.lifespan` starts user reconciliation (Kratos) and the
  verification stale-session sweeper. Both run until cancellation.
* Creating/retrying a batch dispatches Celery task
  `app.worker.generate_batch_keys`; dispatch failure marks the job `FAILED`.
  The worker locks the job/batch, creates credentials in chunks of 500,
  reaches `READY` only when credential count equals `planned_qty`, and is
  idempotent for existing credentials. `CANCELLING` supports safe deletion
  around an in-flight chunk.
* The job publishes `batch.preparation_updated` to Redis at creating,
  generating/progress, ready, failed and cancelling transitions. The realtime
  process subscribes and fans it out to all SSE clients. No other module calls
  `publish_event`.
* Audit records are written in the same transaction as all mutable domain
  operations in users, PAK, defects, KG, batch and production orders.
  The audit read router is the intentional exception: it instantiates
  `AuditRepository` directly for a read-only search.

## Business logic outside the nominal service layer

* Repositories encode more than storage: batch receipt totals/listing exclude
  voided rows; production-order list totals aggregate *current* batches;
  KG derives its display state from the latest verification and shipment data;
  verification repositories take row/advisory-style locks for concurrent open
  flows; user reconciliation uses optimistic `version` updates with
  `SKIP LOCKED`.
* Routers are mostly adapters (validation, authorization and response
  projection). `batch/routers/common.py` additionally composes batch totals,
  job state and related user/order/KG response data; verify it when moving
  query boundaries. `audit/router.py` has the direct repository exception
  above.
* External consistency lives in services: user and PAK provisioning compensate
  Kratos/Hydra changes when DB/audit work fails; PAK deletion removes its Hydra
  client before the local record; machine authentication throttles `last_seen`.

## Rules evidenced by tests (preserve during refactor)

* Batch changes require manager/admin; non-admin owners get a 60-minute edit
  window. Archived batches reject mutations; completed batches reject new
  production work but permit existing document correction. A batch cannot be
  deleted if it has receipts, shipments, scrapped KG or verification history.
  Shipment completion requires items; only packed KG from the same batch may
  be added; voiding a completed shipment restores packed KG without
  overwriting an unexpected state.
* A verification run is exclusive by KG and by PAK slot. Same-location open
  and same-result completion retries are idempotent; a stale run is closed as
  `INCOMPLETE`; only one step may run; `PASSED` session completion requires
  every declared step passed. Session ownership is hidden from other PAKs.
* Defect groups cannot archive while active types remain; types cannot be
  created/restored under an archived group. PAK/test catalogue observation
  rejects unknown or archived groups.
* PAK access keys are encrypted; inactive/archived PAK tokens fail. PAK and
  KG deletion is prevented by verification history. LoRaWAN ciphertext has
  authenticated context tied to DevEUI/configuration and a unique nonce.
* The bootstrap administrator is preserved; users cannot deactivate/delete
  themselves; archive deactivates but restore does not reactivate. Reconciler
  avoids blocking API edits and suppresses duplicate audit records.
* Production-order deletion is based on current membership, while reporting
  aggregates current attached batches; archived orders can be detached and a
  manager may reassign an eligible completed batch.
