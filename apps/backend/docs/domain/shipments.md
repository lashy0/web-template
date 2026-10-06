# Shipments

A shipment sends packed KG units of one batch. Like a receipt,
it lives under its batch at `/batches/{batchId}/shipments`; unlike a receipt,
it names its units by DevEUI, so the shipment of every unit is known. An
order made of several batches is shipped as one shipment per batch.

The database numbers shipments in sequence across all batches (`number`) for
paperwork; a shipment also keeps a comment. It keeps no recipient or waybill
number: the paperwork lives outside the application.

## Lifecycle

```
open ──complete──> completed
  │                    │
  └──void──> voided <──┘ (within 60 minutes of completion)
```

1. `POST /batches/{batchId}/shipments` opens a shipment.
2. Units are added while it is open:
   - `POST .../{shipmentId}/items` with `{"codes": [...]}` adds units by DevEUI
     or short ID in any case, as scanned. Each code is added or rejected on
     its own; the answer lists the added DevEUIs, the rejected codes with a
     reason and the shipment with its new `quantity`. A unit held by another
     shipment is rejected with that shipment's `shipmentNumber`. One request
     takes up to 1 000 codes.
   - `POST .../{shipmentId}/items/packed` adds every packed unit of the batch
     that is in no other shipment, in one statement; `quantity` in the answer
     shows the result.
   - `DELETE .../{shipmentId}/items/{devEui}` takes a unit out again.

   Each unit records who added it (`addedBy` in `GET .../{shipmentId}/items`).
3. `POST .../{shipmentId}/complete` with `{"expectedQuantity": n}` ships the
   units: each goes from `packed` to `shipped`. `n` is the count the user
   saw; several people may fill one shipment, and when it holds another count
   by then, nothing is shipped and the answer is
   `batch_shipment_quantity_changed`. The client reads the shipment again and
   lets the user confirm the new count. The shipment records who completed it
   (`completedBy`).
4. `POST .../{shipmentId}/void` with a reason cancels the shipment. It stays in
   the list, its units are released, and units it had shipped return to
   `packed`. The shipment records who voided it (`voidedBy`).

## When a unit may be added by code

The rules are checked in this order; the first that fails is the reason.

| Rule | Reason |
|---|---|
| the unit exists | `batch_shipment_kg_not_found` |
| it belongs to the shipment's batch | `batch_shipment_kg_other_batch` |
| it is not in this shipment yet, also not through another code of the same request | `batch_shipment_kg_already_added` |
| it is in no other shipment that is not voided | `batch_shipment_kg_in_other_shipment` |
| it is `packed` | `batch_shipment_kg_not_packed` |

A partial unique index on `batch_shipment_items (dev_eui) WHERE voided_at IS
NULL` keeps a unit in at most one shipment that is not voided, whatever the
application checks; adding all packed units skips a unit that a concurrent
request added first. A shipped unit is always in its completed shipment, so it
cannot be added anywhere else.

## Changing a shipment

| Action | Allowed when |
|---|---|
| create | batch not archived; a completed batch may ship |
| edit the comment | batch not archived; shipment open; `expectedUpdatedAt` is its `updatedAt` (see [concurrent edits](../concurrency.md)) |
| add or remove units | batch not archived; shipment open |
| complete | batch not archived; shipment open and not empty; it holds `expectedQuantity` units |
| void | batch not archived; shipment not voided; if completed, within 60 minutes of completion |

An archived batch answers `batch_archived`, a completed shipment
`batch_shipment_completed`, a voided one `batch_shipment_voided`, an empty one
on completion `batch_shipment_empty`, one whose count changed
`batch_shipment_quantity_changed`. The void window applies to everyone with
the permission (`SHIPMENT_VOID_WINDOW` in
`app/domain/production/services/_batch_shipment.py`) and answers
`batch_shipment_void_window_expired` once closed. There is no editing window
for an open shipment: it is a draft until it is completed.

A batch with shipments, voided ones included, cannot be deleted
(`batch_in_use`).

## Counts

The batch shows `packedQty`, which keeps counting shipped units, and
`shippedQty`, the units shipped by completed shipments. The units in stock are
`packedQty - shippedQty`. `/kg/units?stateIn=shipped` lists shipped units.

## Locks

Every change takes a shared lock on the batch, so it cannot be archived
meanwhile, and then locks the shipment row. Adding by code then locks the
units `FOR UPDATE`, in the order packing takes them.

## Audit and access

The audit log records `batch_shipment.created`, `batch_shipment.updated`,
`batch_shipment.completed` (with the quantity) and `batch_shipment.voided`
(with the quantity, the reason and whether it had been completed); each entry
names the batch. Adding and removing units is not logged: an open shipment is
a draft, and its completion records what was shipped.

Reading needs `batches.read`; the changes need `batches.shipments.create`,
`.update`, `.complete` and `.void`. Administrators and managers have them;
packers do not.
