# Batches, DevEUI allocation and receipts

A batch is a production run of KG units. Creating it allocates a contiguous
DevEUI range and registers one `KgUnit` per DevEUI in the same transaction.

## DevEUI allocation

A DevEUI is the ten-hex-digit prefix of a `KgPrefix` followed by a
six-hex-digit serial, so a prefix holds serials `000001` to `ffffff`.

- `KgPrefix.next_serial` is the next free serial. Creating a batch locks the
  prefix row (`SELECT … FOR UPDATE`), takes `planned_qty` serials from it and
  moves the counter; concurrent batches of one prefix wait for each other.
- **A DevEUI is never issued twice.** The counter only grows: deleting a batch
  does not return its range, and a prefix that has allocated DevEUIs cannot be
  deleted (`kg_prefix_in_use`), only archived. Recreating it would restart the
  counter.
- A batch stores `first_serial`; its range is `first_serial` to
  `first_serial + planned_qty - 1`. `planned_qty` has no limit of its own; a
  batch larger than the free serials of its prefix is refused
  (`dev_eui_range_overflow`).
- `GET /batches/dev-eui-range-preview` shows the range the next batch would get
  without reserving it.

## KG units

`/kg/units` lists the units of all batches (filter by `batchIdIn`, `stateIn`,
search by DevEUI or short ID) and addresses one unit by its DevEUI in any case.
The routes are read-only: a unit is `registered` or `scrapped`, and only
production processes change it; users cannot edit or delete units. The
activation type and LoRaWAN version shown with a unit are its batch's: every
unit of a batch is provisioned the same way, so they are stored once.

## LoRaWAN keys

Keys are not stored. `app.lib.lorawan.generate_credentials` derives them from
the DevEUI with the legacy algorithm that devices in the field were flashed
with, so any consumer computes them on demand. The batch stores only the
activation type, the LoRaWAN version and a random JoinEUI.

## Changing a batch

| Action | Allowed when |
|---|---|
| edit name, description, daily plan | not archived, within 60 minutes of creation |
| assign or detach a production order | not archived; the order is not archived |
| complete | not archived, not completed |
| archive, restore | always |
| delete | not archived, not completed, within 60 minutes of creation, no receipts (voided ones included), every KG unit still registered |

The 60-minute window applies to everyone with the permission. The service
checks it (`BATCH_EDIT_WINDOW` in `app/domain/production/services/_batch.py`);
after it closes, edits and deletion answer `batch_edit_window_expired`.

A batch that cannot be deleted answers `batch_in_use`; archive it instead.

Catalog entries referenced by batches cannot be deleted: a used KG version
answers `kg_version_in_use`, a production order with batches
`production_order_in_use`. Archive them instead. Foreign keys with
`ON DELETE RESTRICT` back these checks.

## Receipts

A receipt records how many KG units of a batch were received from production.
It counts units and names no DevEUIs. Receipts live under their batch at
`/batches/{batchId}/receipts`, and the batch shows their sum as `receivedQty`.

- **Receipts never exceed the plan.** Non-voided receipts of a batch add up to
  at most `planned_qty`; a receipt or a correction beyond it answers
  `batch_receipt_quantity_exceeded` with the quantity still open. Every change
  locks the batch row first, so concurrent receipts cannot overshoot together.
- **A receipt is voided, not deleted.** Voiding needs a reason, keeps the
  receipt in the list (`?voided=true|false` filters it) and stops counting its
  quantity, which frees it for another receipt.

| Action | Allowed when |
|---|---|
| create | batch not archived, not completed; within the planned quantity |
| edit quantity, comment | batch not archived; receipt not voided; within 60 minutes of the receipt's creation; within the planned quantity |
| void | batch not archived; receipt not voided; within 60 minutes of the receipt's creation |

As with batches, the window applies to everyone with the permission
(`RECEIPT_EDIT_WINDOW` in `app/domain/production/services/_batch_receipt.py`)
and answers `batch_receipt_edit_window_expired` once closed. A voided receipt
answers `batch_receipt_voided`.
