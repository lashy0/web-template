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
`otkIn`, the dates `lastVerificationAfter`/`Before`, `packedAfter`/`Before` and
`shippedAfter`/`Before` (when its shipment completed), search by DevEUI or short
ID) and addresses one unit by its
DevEUI in any case. The routes are read-only: a unit is `registered`,
`packed`, `shipped` or `scrapped`, and only production processes change it;
users cannot edit or delete units. `otkStatus` and `lastVerificationAt` come
from verification on OTK-line PAKs; see [verification](verification.md).
`runningOtk` is the verification running on an OTK-line PAK now (its PAK and
slot), or `null`: `otkStatus` keeps the last finished result until it ends.
`otkIn` takes OTK results and `running`, which matches the units on a PAK
whatever their result; a unit matching any of the values is listed, so
`otkIn=running&otkIn=failed` lists the units on a PAK and those that failed.
The batch counts the units whose OTK passed as `otkPassedQty`, packed and
shipped ones included since packing needs a passed OTK, and the unpacked units
whose OTK failed as `otkFailedQty`; scrapped units count in neither.
`shipment` is the completed shipment that shipped the unit (its `number` and
`completedAt`), or `null` while the unit is not shipped; see [shipments](shipments.md).
`packedAt` and `packedBy` come from [packing](packing.md), and the batch
counts its packed units as `packedQty`, shipped ones included.
The batch's [shipments](shipments.md) move units to `shipped`, and the batch
counts them as `shippedQty`. The
activation type and LoRaWAN version shown with a unit are its batch's: every
unit of a batch is provisioned the same way, so they are stored once.

`GET /kg/units/{devEui}/timeline` tells what happened to a unit, oldest first:

| `kind` | When | Details |
|---|---|---|
| `registered` | the batch was created | `actor`: who created it |
| `otk_running` | a verification on an OTK-line PAK started and still runs | `session` |
| `otk_passed`, `otk_failed` | a verification on an OTK-line PAK ended so | `session`; `failedChecks` names the failed steps in step order |
| `otk_incomplete` | the PAK's last report in the unit's latest OTK-line verification, which the system closed as incomplete | `session` |
| `packed` | the unit was packed | `actor`: the packer |
| `shipment_added` | the unit is in a shipment still open | `shipment` |
| `shipped` | its shipment was completed | `shipment` |
| `shipment_voided` | that completed shipment was voided; the unit is packed again | `shipment` |

Verifications on engineering PAKs, aborted and incomplete ones do not change
the unit and are left out. The one exception is `otk_incomplete`: it tells why
the unit still waits for OTK, so it is there only while that verification is
the unit's latest on an OTK-line PAK. The unit's sessions are listed by
`GET /verification/sessions?devEuiIn=…`. Receipts count units without
DevEUIs, so they are not events. A shipment voided before completion never
moved the unit and is left out too.

## LoRaWAN keys

Keys are not stored. `app.lib.lorawan.generate_credentials` derives them from
the DevEUI with the legacy algorithm that devices in the field were flashed
with, so any consumer computes them on demand. The batch stores only the
activation type, the LoRaWAN version, a random JoinEUI and its two
[multicast groups](multicast.md), chosen at creation and never changed.

`GET /kg/units/{devEui}/credentials` shows the keys of one unit to
administrators (`kg_units.read_credentials`); `kg_units.read` alone does not
include them. It answers `Cache-Control: no-store` and is not audited. The
response has one shape per activation, told apart by `scheme`; each has
`devEui` and only the fields its activation uses:

| `scheme` | Fields |
|---|---|
| `otaa-1.0` | `joinEui` (the AppEUI), `appKey` |
| `otaa-1.1` | `joinEui`, `appKey`, `nwkKey` |
| `abp-1.0` | `devAddr`, `nwkSKey`, `appSKey` |
| `abp-1.1` | `devAddr`, `fNwkSIntKey`, `sNwkSIntKey`, `nwkSEncKey`, `appSKey` |

The generator also returns a DevAddr for OTAA and an AppKey for ABP, which
these activations do not use; the route leaves them out.

## Changing a batch

| Action | Allowed when |
|---|---|
| edit name, description, daily plan | not archived, within 60 minutes of creation |
| assign or detach a production order | not archived; the order is not archived |
| complete | not archived, not completed |
| archive, restore | always |
| delete | not archived, not completed, within 60 minutes of creation, no receipts or shipments (voided ones included), no verification sessions, every KG unit still registered |

The 60-minute window applies to everyone with the permission. The service
checks it (`BATCH_EDIT_WINDOW` in `app/domain/production/services/_batch.py`);
after it closes, edits and deletion answer `batch_edit_window_expired`.

A batch that cannot be deleted answers `batch_in_use`; archive it instead.

Every change written to the audit log of a batch, its receipts or shipments,
packing a unit, changing the units of a shipment, and a session ended on an
OTK-line PAK publish the realtime event `batch.changed` with the `batchId`; see
[realtime events](../realtime.md). A batch page rereads the batch and its KG
units on it.

Catalog entries referenced by batches cannot be deleted: a used KG version
answers `kg_version_in_use`, a production order with batches
`production_order_in_use`, a used multicast group `multicast_group_in_use`.
Archive them instead. Foreign keys with
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
  receipt in the list (`?voided=true|false` filters it, `searchString` finds a
  comment) and stops counting its quantity, which frees it for another
  receipt.

| Action | Allowed when |
|---|---|
| create | batch not archived, not completed; within the planned quantity |
| edit quantity, comment | batch not archived; receipt not voided; within 60 minutes of the receipt's creation; within the planned quantity; `expectedUpdatedAt` is its `updatedAt` (see [concurrent edits](../concurrency.md)) |
| void | batch not archived; receipt not voided; within 60 minutes of the receipt's creation |

As with batches, the window applies to everyone with the permission
(`RECEIPT_EDIT_WINDOW` in `app/domain/production/services/_batch_receipt.py`)
and answers `batch_receipt_edit_window_expired` once closed. A voided receipt
answers `batch_receipt_voided`.
