# Packing

Packing is the last production step: a KG unit that passed OTK gets its label
and is marked `packed`. Packing is final; there is no unpacking, and a packed
unit keeps `packedAt` and `packedBy` for good. Shipments take packed units only.

## Workstation flow

1. The packer scans the unit. `GET /packing/units/{code}` accepts the DevEUI
   or the short ID (`ab1-000001`) in any case and returns what goes on the
   label (DevEUI, short ID, the batch's JoinEUI) with `canPack` and
   `blockedBy`.
2. The workstation prints the label itself; the server does not know whether
   printing succeeded.
3. `POST /packing/units/{devEui}/pack` marks the unit packed and writes
   `kg.packed` to the audit log. Repeating it answers
   `packing_kg_already_packed`: the workstation then offers a reprint.

web-otk confirmed packing with a challenge code that the browser requested
and sent back in the same flow, and it logged the start of every print. Both
proved nothing and are not carried over.

## When a unit may be packed

The rules are checked in this order; `blockedBy` names the first one that
fails, and packing answers with the same code.

| Rule | Code |
|---|---|
| the unit is not packed yet | `packing_kg_already_packed` |
| the unit is not scrapped | `packing_kg_scrapped` |
| its batch is not archived; a completed batch may be packed | `packing_batch_archived` |
| no OTK-line PAK is verifying it right now | `packing_otk_in_progress` |
| its `otkStatus` is `passed` | `packing_otk_not_passed` |

`otkStatus` comes from the last passed or failed session on an OTK-line PAK
(see [verification](verification.md)), so a unit that failed a retest cannot
be packed on an earlier pass. A session on an engineering PAK does not block
packing. An abandoned OTK-line session blocks the unit until the stale-session
task closes it.

Packing is not limited by the batch's receipts.

## The other direction

An OTK-line PAK cannot open a session for a packed unit
(`verification_kg_packed`); an engineering PAK can, and its sessions stay
history only.

## Locks

Packing takes a shared lock on the batch and then locks the unit
`FOR UPDATE`, in the order verification sessions are opened. The unit lock
conflicts with the key-share lock a PAK holds while opening or finishing a
session, so a unit is never packed while an OTK-line session starts on it.

## Counts and access

The batch shows its packed units as `packedQty`; `/kg/units?stateIn=packed`
lists them. Administrators and packers pack (`packing.pack`); the packing
routes need nothing else, so a packer does not read the KG unit list.
