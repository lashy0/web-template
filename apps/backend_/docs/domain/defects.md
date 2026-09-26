# Defect catalog

The defect catalog classifies what verification finds. It has two levels:

- **Defect groups** (`/defects/groups`) — a class of defects such as radio or
  power faults. A PAK reports a failed check by the group's `code`, so the code
  is matched exactly, case included.
- **Defect types** (`/defects/types`) — a specific defect inside a group, with
  a description, a possible cause and the action an engineer should take.

## Codes

| | Group | Type |
|---|---|---|
| length | up to 32 characters | up to 64 characters |
| format | no whitespace; surrounding spaces are trimmed | same |
| unique | across groups (`defect_group_code_taken`) | across the whole catalog, not only its group (`defect_type_code_taken`) |
| changes | never after creation | never, and the type never moves to another group |

A PAK and the verification history refer to groups by code, so a code stays
fixed; rename the group instead. A code a PAK reports that matches no active
group is accepted and flags the check; see [verification](verification.md).

## Archiving and deletion

| Action | Allowed when |
|---|---|
| edit a group or type | it is not archived (`defect_group_archived`, `defect_type_archived`) |
| create a type | its group exists and is not archived (`defect_group_archived`) |
| archive a group | all of its types are archived (`defect_group_has_active_types`) |
| restore a type | its group is not archived (`defect_group_archived`) |
| restore a group | always; its types stay archived until restored one by one |
| delete a group | it has no types, archived ones included, and no PAK check or verification step refers to it (`defect_group_in_use`) |
| delete a type | always, while nothing refers to it |

Creating or restoring a type takes a shared lock on the group row, and
archiving the group locks the row for update, so a type cannot slip into a
group while it is being archived. A group reports `typesCount` and
`activeTypesCount`, computed in the same query that reads it.

Administrators manage the catalog; managers and engineers read it.
