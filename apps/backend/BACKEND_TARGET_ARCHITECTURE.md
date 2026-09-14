# Целевая архитектура backend

## Статус и цель

Этот документ фиксирует **целевую архитектуру и порядок миграции**, а не
инструкцию по механическому перемещению текущих файлов. До окончания миграции
публичные HTTP-маршруты, контракты API, таблицы и поведение из тестов остаются
совместимыми с текущей системой.

Цель — модульный монолит с бизнес-контекстами и небольшими use cases вместо
feature-модулей, фасадов `*ManagementService` и долгоживущих сервисов. Один
use case — одна бизнес-операция либо связанная read-модель. Он получает
зависимости через конструктор, но не создаёт сессию БД и не выполняет
`commit()`/`rollback()` сам.

`production` является одним context с тесно связанными subdomain'ами:
batch, KG и production order, а также документами поступления/отгрузки и
preparation. Поэтому прямое взаимодействие между его subdomain'ами допустимо
через их внутренние API/repository API в рамках общего UoW; искусственно превращать каждое
такое обращение в межконтекстное событие или HTTP-вызов не следует.

## Целевое дерево `app/`

Структура намеренно плоская. Папка `commands/` нужна для небольших mutating
use cases; `rules.py`, `queries.py` и `repository.py` создаются, когда у
subdomain есть соответствующая ответственность. Не создавать пустые
`domain/application/infrastructure/presentation` или `ports.py` ради шаблона.
Существующие SQLAlchemy models остаются моделями persistence и переносятся
вместе с context: в этом рефакторинге не появляется параллельная цепочка
`SQLAlchemy model -> domain entity -> mapper`.

```text
app/
  api/                                  # только composition корневых routers, errors/deps
  bootstrap/                            # composition root и lifecycle процессов

  contexts/
    production/
      batches/
        model.py                         # existing SQLAlchemy Batch-related models
        rules.py                         # Batch lifecycle/authorization rules
        repository.py
        queries.py
        schemas.py
        router.py                        # existing /batches API adapter
        commands/
      kg/
        model.py
        rules.py                         # state/prefix/version allocation rules
        repository.py
        queries.py
        schemas/
        router.py                        # existing /kg API adapter
        commands/
      production_orders/
        model.py
        repository.py
        queries.py
        schemas.py
        router.py
        commands/
      receipts/                         # Batch subdomain, not a separate context
        repository.py
        queries.py
        schemas.py
        router.py
        commands/
      shipments/                        # Batch subdomain, not a separate context
        repository.py
        queries.py
        schemas.py
        router.py
        commands/
      preparation/
        model.py                         # existing BatchKeyGenerationJob during migration
        rules.py                         # evidenced job transitions only
        repository.py
        commands/                        # retry, process chunk, mark ready/failed, deletion flow
        worker_entry.py                  # invoked by infrastructure Celery task

    quality/
      verification/
        model.py
        rules.py                         # session/step lifecycle rules
        repository.py                    # includes SQL locks and SKIP LOCKED claims
        queries.py
        schemas/
        router.py
        commands/
      defects/
        model.py
        rules.py
        repository.py
        queries.py
        schemas.py
        router.py
        commands/
      tests/
        model.py                         # current SQLAlchemy model/table: PakTest/pak_tests
        repository.py
        queries.py
        schemas.py
        router.py                        # retains /pak/tests
        commands/                        # observation from a PAK

    equipment/
      pak/
        model.py
        rules.py                         # device/access-key lifecycle
        repository.py
        queries.py
        schemas.py
        router.py
        commands/
        contracts.py                     # real external/context boundaries only

    identity/
      users/
        model.py
        rules.py
        repository.py
        queries.py
        schemas.py
        router.py                        # /users and /auth/me adapters/projections
        commands/
        contracts.py                     # Kratos identity boundary

  components/
    keygen/
      types.py                           # canonical LoRaWAN/DevEUI value types
      dev_eui.py                         # pure parse/normalization/range helpers
      crypto.py                          # AES-GCM serialization/cipher and context
      generator.py                       # deterministic LoRaWAN credential generation
      exceptions.py

  audit/
    model.py                             # existing SQLAlchemy AuditEvent
    repository.py
    writer.py                            # TransactionalAuditWriter
    schemas.py
    router.py

  shared/
    security/                            # principal, role, permission registry, auth deps/contracts
    events.py                             # typed notification envelopes, if a shared type is useful
    uow.py                                # optional small transaction helper API

  infrastructure/
    database/                            # engine/session factory/unit-of-work implementation
    redis/                               # Redis client + notification publisher/subscriber adapter
    workers/                             # Celery app and task decorators/dispatch adapter
    realtime/                            # SSE process, broadcaster and Redis subscription adapter
    kratos/                              # SessionVerifier/IdentityManager adapter
    hydra/                               # OAuthClientManager/TokenIntrospector adapter

  platform/
    health/                              # liveness/readiness application + presentation
  core/                                  # settings, logging, version, base exceptions
  middleware/
```

`receipts` and `shipments` intentionally live under `production`, not as
independent contexts: their aggregate root and authorization/lifecycle are
Batch. They may use folders to keep commands small. `preparation` is separate
inside production because its job lifecycle has a different execution model
(worker, chunks, cancellation) despite owning rows tied to a Batch.

## Placement of existing modules and responsibilities

| Current module/responsibility | Target location | Decision and ownership |
| --- | --- | --- |
| `batch` | `contexts/production/batches`, with receipt/shipment commands under `production/receipts` and `production/shipments` | Batch owns production lifecycle, batch configuration and the documents' authorization rules. Preparation job is extracted below. |
| `kg` | `contexts/production/kg` | Owns `KgUnit`, prefixes, versions, physical state and persistence of encrypted LoRaWAN credentials. It may use batch/order internals because all are production. |
| `production_order` | `contexts/production/production_orders` | Owns order lifecycle. Current-batch totals are a production read model, not a copied denormalized aggregate. |
| `verification` | `contexts/quality/verification` | Owns sessions, steps, locking protocol and stale-run closure. It consumes KG, PAK and test-catalog contracts. |
| `defects` | `contexts/quality/defects` | Owns groups/types and their archive rules. |
| `pak` device/provisioning/credentials/authentication | `contexts/equipment/pak` | Owns PAK device, local encrypted access key and Hydra OAuth-client lifecycle. It exposes machine identity/authorization contract to verification. |
| `PakTest` / PAK test catalogue | `contexts/quality/tests` | Logical move only: retain the `PakTest` name, `pak_tests` table and `/pak/tests` API. Catalogue continues to be created/updated exclusively by observation from a PAK; it is quality vocabulary because it binds test name/label to a defect group. |
| `users` | `contexts/identity/users` | Owns user projection, bootstrap, provisioning/reconciliation orchestration and user lifecycle. |
| `auth` roles/principal/contracts | `shared/security` | Role and principal are cross-cutting policy vocabulary. Kratos/Hydra concrete clients remain infrastructure. `/auth/me` is an identity presentation adapter, not a separate auth context. |
| feature permission enums and central `auth/permissions.py` union | local `permissions.py` plus `shared/security/permissions.py` | Each context owns its permission atoms; the shared registry builds the immutable union and resolves a role. No context imports another context's permission enum. |
| `audit` | top-level `audit` | A cross-cutting append-only ledger, deliberately outside a business context. It participates synchronously in the caller's transaction. |
| `lorawan` | `components/keygen` plus `production/kg` persistence | Crypto, credential generation and canonical value types are pure component code. Credential rows/access are KG. Batch LoRaWAN configuration is batches. |
| DevEUI normalization | `components/keygen/dev_eui.py` | Pure lowercase/format/range conversion is a LoRaWAN value-type concern. Prefix selection, uniqueness and allocation sequence are `production/kg` business/concurrency concerns. |
| batch key-generation job | `contexts/production/preparation` | Owns `BatchKeyGenerationJob`, state machine, chunks, retry/idempotency/cancellation/progress. It may call production KG repositories in the same UoW. |
| Celery task and task dispatch | `infrastructure/workers` | Thin inbound/outbound adapters: task parses `batch_id` and invokes preparation use case; dispatch is a port adapter. No Batch/KG business policy in a task. |
| Redis event publishing, SSE app | `shared/events` contracts + `infrastructure/redis`/`infrastructure/realtime` adapters | Realtime is a post-commit delivery concern, not a production aggregate. |
| `health` | `platform/health` | Platform observability, not a domain context. |

### Deliberate boundary decisions

1. **LoRaWAN credentials.** `LoRaWanCredentials` stays a one-to-one KG
   persistence record. The component returns/serializes credentials and
   authenticated-encryption context; a KG/preparation repository writes the
   encrypted row. Thus the component knows neither `Batch`, SQLAlchemy, Celery,
   Redis nor job status.
2. **DevEUI.** Canonicalization must have one pure implementation in
   `components/keygen`; it is used at API boundaries and before persistence.
   `AllocateKgForBatch` owns allocation of a contiguous range and uses a
   production/KG advisory lock. It is not moved into keygen.
3. **`PakTest`.** Observation happens while PAK executes a verification step,
   but the result is a quality test catalogue constrained by a quality defect
   group. The catalogue remains observation-driven; do not add curator writes,
   rename its public API, or change its DB schema in this refactor. Within
   `quality`, verification may call the tests API in the same UoW; no automatic
   port is needed for that intra-context interaction.
4. **Permissions.** Authorization stays at presentation/use-case entry:
   router resolves principal, then invokes the command with it (or uses a
   command authorization policy). Rules that depend on object state, e.g.
   owner + edit window, are domain rules called by the command. Never move the
   global permission union into a feature context.

## Dependency and import rules

### Allowed directions

```text
HTTP/SSE/Celery adapter
  -> application command/query
  -> domain rules + context repository/query port + outbound port
  -> infrastructure adapter

application use case (context A)
  -> public contract/port of context B
  -> adapter implementing that contract (wired by bootstrap)
```

The composition root (`bootstrap` and `app/api`) is the only place allowed to
know concrete implementations from several contexts. `infrastructure` may
depend on shared contracts and a port it implements, but never on an
application use case's internals to make a business decision.

Concrete rules suitable for automated import checks:

| Importer | May import | Must not import |
| --- | --- | --- |
| `<subdomain>/rules.py` | standard library, `shared` value types, `components/keygen` where applicable, its SQLAlchemy model for state predicates | FastAPI, Redis/Celery/Kratos/Hydra, router, another context's model/repository |
| `<subdomain>/commands/*` and `queries.py` | own model/rules/repository, `shared/security`, `audit.writer`, explicitly exported contract of another context | another context's private persistence implementation (model/repository) or router |
| `<subdomain>/repository.py` | its SQLAlchemy models, SQLAlchemy and DB shared base | repositories/models of another context except an explicitly named production read query needed by the common UoW |
| `<subdomain>/router.py` | request/response schemas, own commands/queries, `shared/security` | direct repository use for mutation; another context's private service/repository |
| `components/keygen` | standard library and narrowly scoped crypto libraries | every `app.contexts.*`, `app.infrastructure.*`, `app.worker.*`, SQLAlchemy, FastAPI, Redis/Celery |
| `audit` | its own types/repository and `shared` | business context ORM models/repositories; audit records scalar snapshots supplied by caller |
| `infrastructure/{kratos,hydra,redis,workers,realtime}` | shared/outbound port contracts and framework/client code | business domain policy or direct repositories (the task adapter may call a public application entry point only) |

Within `contexts/production`, `batches`, `kg`, `production_orders`, receipts,
shipments and preparation may use each other's normal internal APIs and the
same UoW. A subdomain should not reach into another subdomain's private
persistence implementation by default; make the required repository method or
named read model an explicit production-internal API instead. This is a local
code-ownership rule, not a mandatory port or event boundary.

The eventual CI checks should: (a) ban imports of another context's private
`model.py`/`repository.py`; (b) ban framework/external-client imports from
`rules.py`; (c) ban all `app.*` imports from `components.keygen`; (d) permit
reviewed production-internal API imports; and (e) require an explicit
`contracts.py`/`public.py` only where a real cross-context or external boundary
exists.

## Future use-case map

The target paths identify implementation targets. Read-only, composable
operations are grouped in `queries.py`; mutating operations get one command
file. Facade methods below are compatibility entry points to delete only after
all callers use the corresponding commands.

### Production — batches, receipts and shipments

| Existing operation | Target |
| --- | --- |
| `BatchService.get`, `list`, `get_key_generation_job(s)`, `deletion_availability` | `production/batches/queries.py` |
| `BatchService.preview_dev_eui_range` | `production/kg/queries.py` (`preview_allocation`) |
| `BatchService.create` | `production/batches/commands/create.py` (uses KG allocation and creates preparation request atomically) |
| `BatchService.update` | `production/batches/commands/update.py` |
| `BatchService.assign_production_order` | `production/batches/commands/assign_production_order.py` |
| `BatchService.complete` | `production/batches/commands/complete.py` |
| `BatchService.set_archived` | `production/batches/commands/set_archived.py` |
| `BatchService.delete` | `production/batches/commands/delete.py` |
| `BatchService.retry_preparation` | `production/preparation/commands/retry.py` |
| `ReceiptService.list_receipts`, `get_received_total` | `production/receipts/queries.py` |
| `ReceiptService.create_receipt` | `production/receipts/commands/create.py` |
| `ReceiptService.update_receipt` | `production/receipts/commands/update.py` |
| `ReceiptService.void_receipt` | `production/receipts/commands/void.py` |
| `ShipmentService.list_shipments`, `list_shipment_items`, count operations, `get_shipped_total` | `production/shipments/queries.py` |
| `ShipmentService.create_shipment` | `production/shipments/commands/create.py` |
| `ShipmentService.update_shipment` | `production/shipments/commands/update.py` |
| `ShipmentService.add_shipment_item` | `production/shipments/commands/add_item.py` |
| `ShipmentService.remove_shipment_item` | `production/shipments/commands/remove_item.py` |
| `ShipmentService.complete_shipment` | `production/shipments/commands/complete.py` |
| `ShipmentService.void_shipment` | `production/shipments/commands/void.py` |

### Production — KG, versions, prefixes, production orders and preparation

| Existing operation | Target |
| --- | --- |
| `KgService.get_with_current_state`, `list`, `list_batch_items` | `production/kg/queries.py` |
| `KgService.set_state` | `production/kg/commands/set_state.py` |
| `KgService.delete` | `production/kg/commands/delete.py` |
| `KgPrefixService` CRUD/archive | `production/kg/commands/{create,update,delete,set_prefix_archived}.py` |
| `KgPrefixService.prepare_allocation`, `preview_allocation` | `production/kg/commands/allocate_for_batch.py` and `queries.py` |
| `KgVersionService` CRUD/archive | `production/kg/commands/{create_version,update_version,delete_version,set_version_archived}.py` |
| `LoRaWanCredentialsService.save/load/existence` | non-public `production/kg/credentials.py`, called by preparation; no HTTP service facade |
| `ProductionOrderService.get/list/get_totals` | `production/production_orders/queries.py` |
| `ProductionOrderService.create/update/set_archived/delete` | `production/production_orders/commands/{create,update,set_archived,delete}.py` |
| `ProductionOrderService.assign` | internal `production/production_orders/public.py` or folded into batch assignment command |
| `BatchKeyGenerationJobService.prepare/generate` | `production/preparation/commands/process_job.py` |
| `_generate_next_chunk`, `_mark_ready`, `_mark_failed` | `production/preparation/commands/{process_chunk,mark_ready,mark_failed}.py`; internal composition, not public endpoints |
| current job cancellation/deletion path | `production/preparation/commands/request_cancellation.py` and `delete_cancelled_batch.py` (preserve the documented current transition table) |

### Quality

| Existing operation | Target |
| --- | --- |
| `VerificationSessionService.get/get_detail/list` | `quality/verification/queries.py` |
| `VerificationSessionService.open_session` | `quality/verification/commands/open_session.py` |
| `VerificationSessionService.complete_session` | `quality/verification/commands/complete_session.py` |
| `VerificationStepService.start_step` | `quality/verification/commands/start_step.py` |
| `VerificationStepService.complete_step` | `quality/verification/commands/complete_step.py` |
| `VerificationCleanupService.expire_stale_sessions` | `quality/verification/commands/expire_stale_sessions.py` (called by scheduled process) |
| `DefectGroupService` and `DefectTypeService` reads | `quality/defects/queries.py` |
| group/type create, update, archive, delete | `quality/defects/commands/{create,update,set_archived,delete}_{group,type}.py` |
| `PakTestCatalogService.get/list` | `quality/tests/queries.py` |
| `PakTestCatalogService.observe(_in_session)` | `quality/tests/commands/observe.py`; normal quality-internal API for verification, not an automatic port |

### Equipment, identity, audit and platform

| Existing operation | Target |
| --- | --- |
| `PakDeviceService.get/list` | `equipment/pak/queries.py` |
| `PakDeviceService.update/set_active/set_archived` | `equipment/pak/commands/{update,set_active,set_archived}.py` |
| `PakProvisioningService.create/delete` | `equipment/pak/commands/{provision,decommission}.py` |
| `PakCredentialService.get_access_key/rotate_access_key` | `equipment/pak/commands/{reveal_access_key,rotate_access_key}.py` |
| `PakAuthenticationService.authorize_machine_access_token` | `equipment/pak/authorize_machine.py` (presentation dependency calls this public API) |
| `UserAccountService.get/list` | `identity/users/queries.py` |
| user update/password/active/archive/delete | `identity/users/commands/{update,set_password,set_active,set_archived,delete}.py` |
| `UserProvisioningService.create` | `identity/users/commands/provision.py` |
| bootstrap/reconciliation | `identity/users/commands/{bootstrap_first_administrator,reconcile_identities}.py` |
| `AuditService.record` / audit search | `audit/writer.py` (`TransactionalAuditWriter.record`) and `audit/presentation` query adapter |
| health liveness/readiness | `platform/health/queries.py` |

## Transaction model

### Unit of work

1. A mutable HTTP command, worker chunk or scheduled cleanup invocation starts
   one `AsyncSession` and one `session.begin()` at its **application entry
   adapter** (a command runner/UoW factory wired in bootstrap). It injects that
   same session-bound repository set and transactional audit writer into the
   use case.
2. The use case may coordinate any number of repositories in its context (and
   production subdomains) through that one UoW. Repositories flush to obtain
   ids/check constraints; they never commit or roll back. A use case also never
   opens a nested independent session for a write.
3. The command runner commits only after the command and its synchronous audit
   append succeed. Any exception rolls back all relational writes. It translates
   expected DB integrity exceptions at the command boundary to the existing
   public conflict errors.
4. Read queries use a short read-only session and do not call a command or an
   audit writer. A query that needs joined data uses a named read model rather
   than entity-by-entity router composition.
5. Bulk/sweeper work retains its current bounded transactions: one stale-session
   batch or one preparation chunk per transaction. It must not hold one DB
   transaction over the entire job or over a network call.

### Audit is transactional, not a post-commit handler

Every mutable business use case explicitly invokes
`TransactionalAuditWriter.record(...)` after determining the final old/new
snapshot and before returning. The audit repository receives the very same
SQLAlchemy session as the business repositories. Therefore business data and
its audit event commit or roll back together. The audit event deliberately
continues to contain scalar actor/entity snapshots and has no FK dependency on
the mutable entity.

Do **not** replace this with an ordinary post-commit domain-event listener:
that would allow the business write to commit without audit history. A future
in-process transactional event helper is allowed only if handlers run inside
the UoW and audit append is a required, exception-propagating handler; no
event bus is introduced as part of this refactor.

### Kratos and Hydra

Neither provider participates in the PostgreSQL transaction, so a false claim
of distributed atomicity is prohibited. Commands involving them use an explicit
orchestration/compensation policy behind `IdentityManager` or
`OAuthClientManager` ports:

* Provisioning captures enough provider data to delete/restore it if the local
  DB + audit transaction fails; this preserves current user/PAK behaviour.
* PAK decommission preserves the current ordering: capture the Hydra client,
  remove it, then delete local PAK + audit in one UoW; if the UoW fails, attempt
  to restore the captured client and surface/log an unreconciled compensation
  failure.
* User identity mutations similarly compensate provider changes when local
  work fails. Reconciliation remains deliberately optimistic and independently
  transactional per user.
* Network I/O must occur outside an open database transaction wherever the
  required ordering permits it. If the current external-first sequence is
  required for security, keep the DB transaction minimal and retain the
  compensator. A durable repair/outbox table is explicitly out of scope for
  this refactor; preserve the current best-effort compensation semantics.

### Events and notifications

| Kind | When | Purpose | Guarantee |
| --- | --- | --- | --- |
| Transactional/domain fact | inside UoW, synchronously | coordinate in-process rule/audit participants | DB + mandatory audit are atomic; no broker publication here |
| Post-commit notification | only after successful UoW exit | request Celery work, best-effort integration notification | never used to create audit; needs retry/idempotency where delivery matters |
| Realtime/progress notification | after the relevant preparation chunk/status transaction commits | Redis `batch.preparation_updated` then SSE fan-out | best effort and non-authoritative; client re-reads job state on reconnect |

Creating or retrying a batch must commit the job state before dispatching the
Celery task. Target adapters publish only after the corresponding transaction
has exited successfully. The current dispatch-failure branch calls its Redis
publisher inside `session.begin()`; when it is moved, retain the same
`FAILED` status/payload but invoke it after commit. This is a notification
ordering correction, not an audit or domain-state change. Each worker progress
notification is already sent after its chunk's state/credential writes commit.

## Cross-context contracts and ports

`contracts.py`/port is created only at a real context or external-system
boundary. It belongs to the consumer that needs the abstraction; the provider
exports a narrow `public.py`/contract. The payload consists of ids and
immutable DTOs/value types, not SQLAlchemy entities. Inside one context,
including all of `production` and quality `verification -> tests`, use a normal
internal API and common UoW instead of inventing a port.

| Consumer | Port / public contract | Provider | Required operation |
| --- | --- | --- | --- |
| identity presentation | `SessionVerifier` | infrastructure/Kratos | validate session -> external identity id |
| identity/users | `IdentityManager` | infrastructure/Kratos | provision/update/disable/delete/list identity and revoke sessions |
| equipment/pak | `OAuthClientManager` | infrastructure/Hydra | provision/delete/rotate/restore OAuth client |
| equipment/pak | `TokenIntrospector` | infrastructure/Hydra | token introspection used by PAK's own public machine-authorization API |
| quality/verification | `KgVerificationPort` | production/kg public contract | canonical KG lookup; lock/use as registered; begin/end verification-related state only if needed |
| quality/verification | `PakAccessPort` | equipment/pak public contract | authenticated PAK identity, active state and PAK id/code |
| equipment/pak decommission | `VerificationHistoryPort` | quality/verification | `has_history_for_pak(id)` |
| production/batches delete | `VerificationHistoryPort` | quality/verification | `has_history_for_batch(id)` |
| production/kg delete | `VerificationHistoryPort` | quality/verification | `has_history_for_kg(dev_eui)` |
| all mutable contexts | `TransactionalAuditWriter` | audit | append snapshot in caller UoW |
| production/preparation | `ProgressNotifier`, `WorkDispatcher` | Redis/Celery adapters | publish after commit; enqueue job after job commit |

Production's normal internal repository/use-case APIs share the same UoW for
atomic Batch/KG allocation, shipment document mutation and order assignment.
This is not a port exception: `production` is one context. It does not permit
`quality` or `equipment` to import production private repositories.

## Keygen and worker architecture

```text
Celery task (infrastructure/workers)
  -> preparation worker adapter/factory
  -> production/preparation ProcessJob / ProcessChunk use case
       -> production KG credential persistence port (same chunk UoW)
       -> components/keygen KeyMaterialGenerator
  -> commit chunk/status
  -> ProgressNotifier (Redis) -> realtime SSE adapter
```

`components/keygen` has a narrow pure API, conceptually:

```text
normalize_dev_eui(value) -> DevEui
derive_range(prefix, first, quantity) -> iterable[DevEui]
generate_credentials(dev_eui, activation_type, lorawan_version) -> Credentials
encrypt/decrypt(credentials, authenticated_context) -> serialized payload
```

It does not receive a session, `Batch`, job id/status, Redis client, Celery
task, `planned_qty`, `chunk_size` or cancellation flag. `production/preparation`
owns all of these: job transition validation, row/advisory locks, allocation
selection, chunk size (currently 500), idempotency for existing credentials,
safe cancellation around an in-flight chunk, progress calculation and the
READY only when `credential_count == planned_qty` transition.

### Current preparation transition table — preserve exactly

This table is extracted from `BatchService`, `BatchKeyGenerationJobService` and
the current worker; it is the required specification before the worker moves.
It documents implementation facts, not proposed new transitions.

| From | Trigger and guard | To | Transactional consequence |
| --- | --- | --- | --- |
| no job | `CreateBatch` | `CREATING` | Batch, LoRaWAN config, all KG rows, one job (`progress=0`) and audit row commit together; Celery dispatch follows commit. |
| `FAILED` | `retry_preparation`, only for manager/admin and non-archived batch | `CREATING` | Reset `progress=0`, clear `error_code`, commit, then dispatch again. Any other source state is a no-op. |
| `CREATING` | worker obtains batch/job `FOR UPDATE` | `GENERATING` | Status changes with existing progress (normally 0), commits; no credential chunk is generated in this transition. |
| `GENERATING` | worker locks job, selects up to 500 KG rows without credentials | `GENERATING` | Generate/save idempotently; existing credential conflict is skipped; recompute `progress = credential_count * 100 // planned_qty` and commit. |
| `GENERATING` | no chunk remains and locked count is exactly `planned_qty` | `READY` | Set `progress=100` and commit. If count differs, remain `GENERATING`; no invented failure/ready transition is allowed. |
| worker exception while preparation runs | job still exists and is not `CANCELLING` | `FAILED` | Preserve progress, set `error_code=batch_key_generation_failed`, commit, then publish failure. The same error path deliberately does not overwrite `CANCELLING`. |
| `CREATING` after a dispatch attempt, or reset `CREATING` after retry | Celery dispatch raises | `FAILED` | Dispatcher failure marks the existing job failed with current progress and the same error code. Current Redis emission occurs in that transaction; target adapter emits identical payload after commit. |
| any non-`READY` job (`CREATING`, `GENERATING`, `FAILED`, or already `CANCELLING`) | eligible `DeleteBatch` reaches preparation branch | `CANCELLING` | Set/preserve progress and commit; publish `CANCELLING`. There is no separate public cancel operation. |
| `CANCELLING` | worker reaches/has released its current locked chunk; delete flow locks batch/job | deleted | Delete registered KG, write `batch.deleted` audit in the cleanup transaction, then delete Batch; cascade removes job/config/credentials. There is no terminal `CANCELLED` status. |
| `READY` or no job | eligible `DeleteBatch` | deleted | No cancellation state: audit, registered-KG deletion and Batch delete occur in the command transaction. |

The worker checks status under the batch/job row locks before every chunk. A
`CANCELLING` job therefore stops further generation; deletion waits out any
in-flight locked chunk before cleanup. Notifications are best effort and
non-authoritative for `CREATING`, `GENERATING`, progress updates, `READY`,
`FAILED`, and `CANCELLING`; after migration they are consistently post-commit
(the current dispatch-failure exception is recorded above).

Use a unique credential primary key and locked job/batch rows as the durable
idempotency mechanism. `process_chunk` must re-read job state after obtaining
the lock, select only KG without credentials, then commit before publishing.
It must never infer completion from an emitted progress event.

## Repository and read-model responsibilities

Repositories are not required to be artificially CRUD-only. Their contract
must distinguish persistence/concurrency mechanics from business policy.

| Current behavior | Target owner | Reason |
| --- | --- | --- |
| SQLAlchemy aggregate loading/saving, `FOR UPDATE`, flush and FK/unique error facts | context-local `repository.py` | Persistence implementation detail; commands translate persistence facts to domain errors. No parallel entity/mapper layer is introduced. |
| `Batch`, receipts, shipments and their joined response data | batches/receipts/shipments repositories plus `production` read models | They are one production aggregate family; router composition moves to a named query/projection. |
| receipt totals excluding voided rows | `production/receipts` read query/repository | This is a documented reporting semantic expressed efficiently in SQL, not a hidden generic repository convention. |
| shipped totals and item counts excluding voided shipments | `production/shipments` read query/repository | Same: SQL is appropriate; command rules decide when documents can change. |
| production-order totals/current membership | `production/production_orders` read model | Aggregate current `Batch.production_order_id` at read time. Do not cache it or treat audit history as membership. |
| KG display state from latest verification data | `production/kg` named `KgCurrentStateReadModel` | Keep SQL window/query expression near the KG read API. It is a projection, not persistent KG state. The current expression does not use shipment data. |
| verification `FOR UPDATE`, deterministic candidate order, advisory locks | `quality/verification/repository.py` (a `locking.py` helper only if it grows independently) | Concurrency mechanism stays SQL-specific; use case states why it is called (exclusive KG/PAK slot). |
| stale-session `SKIP LOCKED` | verification repository batch-claim method | Infrastructure work-claim mechanism; `ExpireStaleSessions` owns cutoff/transition policy. |
| user `version` compare-and-update and `SKIP LOCKED` reconciliation selection | identity/users repository concurrency methods | Optimistic concurrency and nonblocking work claim remain technical mechanisms; reconcile use case owns conflict/audit semantics. |
| prefix allocation advisory lock/max DevEUI | production/kg repository `AllocationLock`/query | Postgres serialization is technical; `AllocateKgForBatch` owns prefix/archive/range business validation. |

Each repository method should name the semantic it provides (`claim_stale_runs`,
`lock_allocation`, `read_current_state_page`) rather than exposing arbitrary
query fragments. Aggregate/read DTOs (`KgListItem`, order totals, batch detail)
reside next to `queries.py` or a small `read_models.py`, not in a router.

### Existing PostgreSQL verification backstops — preserve exactly

The following current database constraints/indexes are part of the
exclusivity design and remain unchanged during this structural refactor:

* Partial unique index `ux_verification_running_by_kg` on
  `verification_sessions(kg_dev_eui) WHERE status = 'RUNNING'`.
* Partial unique index `ux_verification_running_by_pak_slot` on
  `verification_sessions(pak_id, slot_no) WHERE status = 'RUNNING'`.
* Unique constraint `uq_verification_steps_session_step_no` on
  `verification_steps(session_id, step_no)`.
* Check constraints `verification_session_slot_no_positive`,
  `verification_session_total_steps_positive`, `verification_step_no_positive`
  and `verification_step_measurement_range_valid`.
* Foreign keys with current deletion semantics: verification session -> KG and
  PAK are `RESTRICT`; step -> session is `CASCADE`; step -> `pak_tests` and
  defect group are `RESTRICT`.
* Supporting indexes `ix_verification_sessions_kg_started_at`,
  `ix_verification_sessions_pak_started_at`,
  `ix_verification_sessions_status_last_activity_at`,
  `ix_verification_steps_test_name`, `ix_verification_steps_status`,
  `ix_verification_steps_pak_test_id`, and
  `ix_verification_steps_defect_group_id`.

`VerificationSessionRepository.lock_session_open()` additionally takes
PostgreSQL transaction advisory locks for canonical keys
`verification:kg:<dev_eui>` and `verification:pak-slot:<pak_id>:<slot_no>`;
it locks candidates in deterministic id order. Stale-session claiming uses
`FOR UPDATE SKIP LOCKED`. Preserve all three layers—advisory locks, row locks,
and partial unique indexes—rather than replacing one with another.

## Business invariants and future owners

The following is a migration specification derived from the existing tests.
No rule may be weakened, removed or silently changed.

| Invariant | Future owner/mechanism |
| --- | --- |
| Batch changes require manager/admin. | `production/batches` command authorization policy; context permission atom + shared role registry. |
| A non-admin may edit only own batch/documents within 60 minutes; admin bypasses the owner/window restriction. | `production/batches/rules.py` and receipt/shipment rules, passed `actor` and clock by command. |
| Archived batch rejects every mutation. | Batch domain rule, called by all mutation commands including documents/preparation as applicable. |
| Completed batch rejects new production work but permits correction of existing documents. | Batch/document domain rules: creation/production commands reject; update/void existing receipt/shipment retain current correction rules. |
| Batch deletion is forbidden with receipts, shipments, scrapped KG or verification history. | `DeleteBatch` use case orchestrates local production queries + `VerificationHistoryPort`; FK/DB constraints remain backstop. |
| Completion requires preparation READY. | `CompleteBatch` use case + preparation job state domain rule. |
| Completing shipment requires at least one item. | `CompleteShipment` use case; item-count repository query is the persistence fact. |
| Shipment items belong to the same batch and an item cannot be assigned to another non-voided shipment. | `AddShipmentItem` command + shipment rules; row locks/unique PK and query provide concurrency backstop. Persistent `KgState` remains only `REGISTERED`/`SCRAPPED`; shipment operations do not require `PACKED`. |
| Completing or voiding a shipment changes shipment-document state only. | Shipment commands preserve the current persistent KG state; they do not transition KG to `SHIPPED` or restore `SHIPPED -> PACKED`. |
| Verification is exclusive by KG and PAK slot. | `OpenVerificationSession` use case plus verification advisory locks, deterministic row locking and existing DB uniqueness constraints. |
| Same-location open retry and same-result completion retry are idempotent. | `OpenVerificationSession`/`CompleteVerificationSession` domain idempotency rules, with locked repository reads. |
| Stale running verification closes as `INCOMPLETE`. | `ExpireStaleSessions` use case; `SKIP LOCKED` claim repository method; clock/cutoff is application input. |
| At most one verification step runs per session. | start/complete step domain rules plus row locks and DB constraint/index where present. |
| `PASSED` session completion requires every declared step passed. | `CompleteVerificationSession` domain rule; step-status count query is repository support. |
| A PAK cannot see/operate another PAK's session. | verification command authorization/ownership rule and session query predicate. |
| Defect group cannot archive while active types remain. | `SetDefectGroupArchived` use case/domain rule; active-type existence query. |
| Type cannot be created/restored under archived group. | type create/archive command + defect-group contract/rule. |
| Test observation rejects unknown or archived defect group. | `quality/tests Observe` command via the normal `quality/defects` internal API, lock query, and configuration error. |
| PAK access keys are encrypted. | equipment/pak credential application service + crypto component/secure configuration; no plaintext persistence. |
| Inactive/archived PAK token fails. | PAK machine authorization use case plus Hydra token port and local active/archive check. |
| PAK and KG deletion is prevented when verification history exists. | PAK/KG delete command through `VerificationHistoryPort`; DB FK RESTRICT remains a final guard. |
| LoRaWAN ciphertext has authenticated DevEUI/config context and a unique nonce. | `components/keygen/crypto.py` domain component; persistence uses its serialized payload and DB one-to-one credential key. |
| Bootstrap administrator is preserved. | identity/users delete/deactivate/archive domain policy + bootstrap command. |
| User cannot deactivate or delete self. | identity/users command authorization/domain policy. |
| Archive deactivates; restore does not reactivate. | `SetUserArchived` use case/domain transition rule and identity-provider orchestration. |
| Reconciler does not block API edits and emits no duplicate audit entries. | reconciliation use case; optimistic version CAS + `SKIP LOCKED`/short UoW repository mechanism; transactional audit only on applied change. |
| Production-order deletion uses current membership; reports aggregate currently attached batches. | delete command (`contains_current_batches`) and order read model; both query current `production_order_id`, not historical audit. |
| Archived order can be detached; manager may reassign an eligible completed batch. | `AssignProductionOrder` batch command/domain rule plus production-order eligibility contract/query. |
| Positive quantities, canonical lowercase DevEUI/prefix, unique identities/codes, single running verification and unique step number remain enforced. | Existing DB `CHECK`, `UNIQUE`, FK and partial/operational constraints stay schema backstops; domain/use-case validation provides meaningful errors; concurrency logic handles races. |

## Recommended migration order

1. **Freeze and characterize.** Approve this document; run the existing unit,
   API and integration tests as the behavior baseline. Add architectural import
   tests only after public boundary packages are introduced. Do not change API
   or schema in this phase.
2. **Introduce seams without moving behavior.** Create the target package
   skeleton, composition/UoW convention, shared security public API and
   transactional audit writer contract. Existing services may call/use these
   seams temporarily, but no duplicate commit boundary is allowed.
3. **Extract pure `components/keygen`.** Move only pure LoRaWAN types,
   normalization, generator and crypto behind characterization tests. Preserve
   byte-level encryption compatibility, authenticated context and error
   behavior; worker still calls the old preparation facade initially.
4. **Migrate production as one vertical slice.** Introduce production
   repositories/read models and commands in order: KG prefix/version/allocation
   -> batch create/update/lifecycle -> receipts/shipments -> production orders
   -> preparation worker. Keep internal production transactions atomic and
   retain endpoint adapters as thin compatibility shims.
5. **Migrate quality.** Move defects, then test catalogue, then verification
   commands/locking/cleanup. Replace direct KG/PAK/Test repository imports with
   explicit contracts while preserving locking and retry behavior.
6. **Migrate equipment and identity.** Move PAK provisioning/credential/token
   policies and user lifecycle/provisioning/reconciliation. Characterize
   Kratos/Hydra compensation before changing orchestration.
7. **Move cross-cutting adapters.** Relocate audit router/repository,
   Redis/realtime and Celery adapters; make realtime publication explicitly
   post-commit. Keep SSE endpoint/API event payload compatible.
8. **Delete compatibility facades and old feature modules.** Only after no
   imports, router composition or worker task targets reference them; enforce
   import rules in CI and remove bridges one bounded context at a time.

## Confirmed preservation boundaries

The following were formerly open questions and are now migration constraints:

* `PakTest` moves logically to `quality/tests`, stays named/stored/exposed as
  today, and remains populated/updated by PAK observation only.
* The preparation transition table above is authoritative. Cancellation occurs
  only through the existing eligible batch deletion flow; no new API, terminal
  job state or transition is introduced.
* Kratos/Hydra keep their current compensating orchestration. No durable outbox
  or repair table is added in this refactor.
* Verification retains the precise constraints/indexes and locking protocol
  listed above.
* KG current state retains the current SQL projection and its existing
  precedence: `SCRAPPED`, then latest verification status (`ON_OTK`, `OTK_PASSED`,
  `OTK_FAILED`, `OTK_ABORTED`, `OTK_INCOMPLETE`), otherwise `REGISTERED`.
  Shipment data does not participate in the current expression and must not be
  added while moving it.
* The unauthenticated SSE `/events` contract, event payload and fan-out scope
  remain unchanged. Realtime security is out of scope.
* Existing SQLAlchemy mapped models move with their contexts. There is no new
  domain-entity/mapper layer unless a separately approved concrete need arises.

## Migration checkpoints

| Checkpoint | Required backend state |
| --- | --- |
| 0 — architecture approved | This document is accepted; existing tests pass; no application behavior, API or schema has changed. |
| 1 — foundations | Target packages and public-contract/UoW conventions exist; routers/tasks still may use compatibility facades; every mutable path has exactly one DB transaction owner and uses transactional audit. |
| 2 — keygen isolated | `components/keygen` has no app/infrastructure dependencies; golden tests prove canonicalization, deterministic generation and AES-GCM compatibility; worker behavior is unchanged. |
| 3 — production migrated | All batch/KG/order/receipt/shipment/preparation routes and worker enter named production commands; batch create/allocation/audit and chunk idempotency remain atomic; no cross-context persistence import escapes production. |
| 4 — quality migrated | Verification/defects/tests use cases and locks are in quality; PAK/KG access happens only through contracts; exclusivity, idempotency and stale sweep integration tests pass unchanged. |
| 5 — equipment and identity migrated | PAK and user commands own provider compensation explicitly; bootstrap/reconciliation behavior and audit atomicity pass integration tests; shared security has the only permission registry. |
| 6 — adapters and notifications migrated | Celery/Redis/SSE are infrastructure adapters; notifications are demonstrably emitted after commit; audit is never asynchronous; health is in platform. |
| 7 — cleanup complete | No production code imports `app.modules.*` or management facades; compatibility bridges are deleted; CI import rules pass; full unit/API/integration suite passes without changed contracts. |

## Final architecture decisions

These decisions are closed for this migration. A coding agent must apply them,
not reopen them while moving code.

* Contexts are the primary boundary; subdomains use the flat
  `model.py`/`rules.py`/`repository.py`/`queries.py`/`router.py`/`commands/`
  layout by default. Extra layers or folders appear only for a concrete need.
* SQLAlchemy models move with their context. No parallel domain entities or
  mappers are introduced.
* Ports/contracts exist only at real external-system or cross-context
  boundaries. `production` is one context with a common UoW; quality
  verification and tests also use a normal internal API.
* `TransactionalAuditWriter` remains explicit in every mutable operation and
  writes in the same DB transaction. No event bus is introduced.
* `components/keygen` remains a pure LoRaWAN component. Preparation owns job
  lifecycle, chunking, idempotency, cancellation and progress; Celery/Redis
  remain adapters outside it.
* `PakTest` remains an observation-driven catalogue in `quality/tests` with
  unchanged table and API; no schema/API naming change is part of this work.
* Current Kratos/Hydra compensations, verification constraints/locks, KG
  current-state semantics and unauthenticated SSE contract are preserved.
  Durable outbox/repair storage and realtime-security work are explicitly out
  of scope.
