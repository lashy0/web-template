# Multicast groups

A KG unit listens to two LoRaWAN multicast groups besides its own address: one
in slot (McGroupID) 0 and one in slot 1, one for firmware updates and the other
for operation. The PAK writes both into the unit together with its keys; see
[verification](verification.md#machine-api).

## Catalog

`/kg/multicast-groups` lists the groups (filter by `groupIdIn`, search by name
or address). A group has a `name`, a `groupId` (0 or 1), an address `mcAddr`,
a downlink `frequencyHz` and `datarate`.

- **The server generates the address and the McKey.** Creating a group takes
  only the name, the group ID and, when they differ from 869 100 000 Hz and
  DR0, the frequency and data rate. Addresses are unique; the McKey is random
  and never changes, nor does the address.
- **Groups are shared.** Several batches may use one group; the batch list
  filters by it with `multicastGroupId`.
- **A used group keeps its radio settings.** Once a batch uses the group, its
  units may already carry it: only the name can change
  (`multicast_group_in_use` otherwise), and the group cannot be deleted, only
  archived. An archived group stays with its batches but cannot be chosen for a
  new one.

| Action | Allowed when |
|---|---|
| create | always; the name is unique (`multicast_group_name_taken`) |
| rename | not archived |
| change group ID, frequency, data rate | not archived, no batch uses it |
| archive, restore | always |
| delete | no batch uses it |

The catalog is read with `multicast_groups.read`, which managers have to choose
the groups of a batch. The keys are for administrators only.

## Keys

`GET /kg/multicast-groups/{id}/keys` (`multicast_groups.read_keys`) returns the
`mcKey` and the session keys derived from it, `mcNwkSKey` and `mcAppSKey`. It
answers `Cache-Control: no-store` and is not audited. Hex values are lower case.

The session keys are not stored. `app.lib.lorawan.derive_multicast_session_keys`
derives them with the algorithm of the legacy service that configured the
devices and network servers in the field: AES-128 of the McKey over a block of
one byte, the address least significant byte first and eleven zero bytes. The
byte is `0x01` for the McNwkSKey and `0x02` for the McAppSKey, the reverse of
LoRaWAN TS005; changing it would break the groups already in use.

## Batches

Every batch names one group of each group ID, `multicastGroup0Id` and
`multicastGroup1Id`, when it is created. A group of the wrong ID answers
`multicast_group_id_mismatch`, an archived one `multicast_group_archived`. The
groups of a batch never change afterwards: its units are provisioned with them.

Every change of a group writes the audit log and publishes
`multicast_group.changed` with the `multicastGroupId`; see
[realtime events](../realtime.md).
