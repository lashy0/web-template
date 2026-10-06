# Audit log

Every audited user change through the API writes one entry to `audit_log` in
the same transaction as the change, so an entry exists exactly when the change
was committed. Entries are never updated or deleted by the application.

## Entry

| Field | Meaning |
|---|---|
| `action` | `<subject>.<verb>`, e.g. `batch.completed`, `user.password_changed`, `kg.packed` |
| `actorId`, `actorLogin`, `actorName` | who acted; the login and name are snapshots and stay after the user is renamed or deleted (`actorId` becomes null) |
| `targetType`, `targetId`, `targetLabel` | what was changed; the label is a snapshot such as a login, a code, a name or a DevEUI |
| `targetName` | a snapshot of the target's name when it has one apart from its label: users, KG versions and prefixes, defect groups and types |
| `details` | action-specific JSON: the changes of an update (below) or the key values of a created or deleted record |
| `ipAddress`, `userAgent` | of the request, when there is one |

Entries without a signed-in user have no `actorId`: `actorLogin` is `cli` for
commands run with `otk` (see `docs/authentication.md`) and the PAK code for
check changes a PAK reports. They have no `actorName` either.

Target types: `user`, `pak`, `production_order`, `kg_prefix`, `kg_version`,
`multicast_group`, `batch`, `batch_receipt`, `batch_shipment`, `kg_unit`, `defect_group`,
`defect_type`, `pak_check`.

## Writing

A controller records a change through the `changes` dependency, a
`ChangeRecorder` (`app/domain/audit/changes.py`), after the service call
succeeded:

```python
await changes.record(
    "kg_prefix.updated",
    db_obj,
    event=KgPrefixChanged(prefix_id=db_obj.id),
    details=details,
)
```

The recorder takes an immutable `Actor` (`app/lib/audit.py`). The typed factories
`actor_of_user` and `actor_of_pak` live with the recorder providers in
`app/domain/audit/deps.py`, keeping model imports out of `app/lib/audit.py`.
They snapshot the user's ID, login and name, or only the PAK code. The app-level
provider supplies the signed-in user as the actor. The machine verification
controller overrides only the `changes` provider with
`provide_machine_change_recorder`: the authenticated PAK supplies `actorLogin`,
while `actorId` and `actorName` are null. Both use the same recorder, which
writes the entry and announces the [realtime event](realtime.md) once the
transaction commits; every recorded change has an event. Requesting `changes`
also requests the unit of work, so the change commits (see
[transactions](transactions.md)). CLI commands use
`AuditLogService.log_action` directly. For a change that is not audited, use
`changes.announce(event)`; it still requests the unit of work and publishes
only after the change commits. A failed handler or commit rolls back the
change and its audit entry and discards the event.

A model whose records are targets mixes in `AuditTarget` (`app/lib/audit.py`)
and declares how entries name it:

```python
class PakDevice(UUIDv7AuditBase, AuditTarget):
    __audit_type__ = "pak"  # targetType
    __audit_label__ = "code"  # targetLabel; __audit_id__ gives targetId, "id" by default
    __audit_name__ = None  # targetName, for a name shown apart from the label
```

`log_action` reads the target's type, id, label and name from these attributes.
Record document-level events only: a shipment's completion records what was
shipped. Adding and removing individual KG units is not audited; it only
announces that the batch changed.

## Changes

An update records what it changed, field by field, in the API's field names:

```json
{"changes": {"name": {"from": "Партия 1", "to": "Партия 1А"},
             "description": {"from": null, "to": "Вторая смена"}}}
```

The controller snapshots the record before and after the service call with
`app/lib/audit.py` and logs only the fields that differ; an update that
changes nothing writes no entry. Values are stored as JSON: enums by value,
ids and decimals as strings, times in ISO 8601. A reference to another record is
stored by its label at the time of the change, such as the production order's
name, so the entry stays readable after that record is renamed or deleted.
Secrets are never recorded; changing them has an action of its own, such as
`user.password_changed` or `pak.access_key_rotated`.

A PAK check that a PAK reports with another defect group records its changes in
the same format.

## Reading

`AuditController` uses the app-level `audit_service`; it declares only its
filter dependencies through `app.lib.deps.create_filter_dependencies`, so
reading and writing share the service configuration.

`GET /audit` lists entries newest first. Only administrators read the log
(`audit.read`). Filters:

- `targetTypeIn`: the entries of a section, e.g. `defect_group` and
  `defect_type` for the defect catalog;
- `targetTypeIn` with `targetIdIn`: the history of one record;
- `actorIdIn`: what a user did;
- `createdAfter`, `createdBefore`: a time range.

A target whose label can be edited, such as a PAK code or a user login, may be
labelled otherwise today than in the entry. The list then adds
`targetCurrentLabel`, read through the target model's `__audit_label__` when the
page is served, so an entry can be matched to the record it concerns; it is
null when the label has not changed or the target has been deleted.
