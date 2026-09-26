# Verification (OTK)

A PAK verifies a KG unit by running a series of checks on it. The PAK reports
each run as a **verification session** made of **steps**, one step per check.
Users only read the history; PAKs write it through the machine API.

## Machine API

PAKs call `/machine/verification/sessions` with a Hydra access token
(`Authorization: Bearer ...`, client credentials of the PAK's OAuth client).
Browser sessions do not apply there. An inactive or archived PAK gets 403.

| Request | Route |
|---|---|
| open a session | `POST /machine/verification/sessions` `{devEui, slotNo, firmwareVersion, totalSteps}` |
| start a step | `POST /machine/verification/sessions/{id}/steps` `{stepNo, checkName, checkLabel, defectGroupCode}` |
| report a step | `PUT /machine/verification/sessions/{id}/steps/{stepNo}` `{status: passed\|failed, measurementValue, measurementMin, measurementMax, measurementUnit}` |
| finish a session | `POST /machine/verification/sessions/{id}/complete` `{status: passed\|failed\|aborted}` |

Every request may be repeated after a lost response: the same report is
answered with the current state, a different one with a 409. A session of
another PAK answers 404.

## Sessions

A KG unit and a PAK slot each have at most one `running` session.

| Opening a session when | Result |
|---|---|
| the unit is unknown | `verification_kg_not_found` |
| the unit is scrapped | `verification_kg_scrapped` |
| the unit's batch is archived | `verification_batch_archived`; a completed batch may be verified |
| the unit already runs in the same slot | that session is resumed |
| the unit runs in another slot, reported within the last 60 minutes | `verification_session_already_running` |
| the unit runs in another slot, idle longer | that session is closed as `incomplete`, a new one starts |
| the slot runs another unit | that session is closed as `incomplete`: the PAK moved on |

A session ends `passed`, `failed` or `aborted` when the PAK finishes it, and
`incomplete` when the system closes it. `passed` needs every step passed; a
running step blocks `passed` and `failed` (`verification_session_incomplete`)
and is aborted with the session on `aborted`. `lastActivityAt` is the PAK's
last report; closing a session as incomplete keeps it.

A PAK may abort a session after the system has already closed it: `aborted`
on an `incomplete` session is answered with the session as it is, not a 409,
because both mean the PAK did not finish it. `passed` or `failed` on it is
still `verification_session_not_running`.

The background task `expire_stale_verification_sessions` runs every minute and
closes sessions idle for `BACKEND_VERIFICATION_SESSION_TTL_MINUTES` (120) as
incomplete, aborting their running step. The 60 minutes above are
`BACKEND_VERIFICATION_SESSION_REOPEN_INACTIVITY_MINUTES` and must be shorter
than the TTL.

## Steps

Steps run one at a time (`verification_step_in_progress`), numbered from 1 up
to the session's `totalSteps` (`verification_step_out_of_range`). A step number
started with another check answers `verification_step_already_exists`; a step
reported again with another result answers
`verification_step_already_completed`. A step keeps the check's name, label and
defect group code as the PAK reported them, so the history does not change
with the catalog.

A step's measurement is optional: a check may report no value, or a value
without a unit or limits. A blank unit is stored as none, and so are limits
of 0 to 0: PAKs report a check without limits that way. The PAK's verdict
decides the step; the value is not checked against the limits, and for some
checks it is a result code rather than a measurement.

## Check catalog

`/verification/checks` lists the checks PAKs run, keyed by `name` and `label`
together: a PAK reuses one name for variants of a check, such as
`TestDimming` with the labels «Проверка диммирования 0%» to «…100%», and each
variant is a check of its own. Starting a step creates the check or updates
its defect group code and `lastSeenAt`; a creation or change is written to
the audit log as `pak_check.created` or `pak_check.updated` with the PAK as
the actor. A PAK that renames a label starts a new check; the old one keeps
its history and stops being seen.

A defect group code that matches no active group (unknown or archived) is
accepted: the step and the check are kept without a group, a warning is
logged, and the check shows `misconfigured: true` (`?misconfigured=true`
filters them) until a PAK reports it again with an active group's code.

## KG OTK status

A KG unit's `otkStatus` is `not_verified` until a session on an **OTK-line**
PAK ends `passed` or `failed`; that result and its time (`lastVerificationAt`)
stay until the next such session. Sessions on engineering PAKs, and aborted or
incomplete sessions, are history only. The PAK's kind is copied into the
session when it opens, so changing the PAK later does not change the meaning
of its sessions.

Not enforced yet: a packed KG unit must not pass OTK on an OTK-line PAK. The
rule arrives with packing.

## Locks and deletion

Opening a session locks the batch (shared), the KG unit, the PAK, then the
running sessions, in that order; finishing one locks the KG unit before the
session, so concurrent reports never deadlock. Starting a step takes a shared
lock on the defect group, like creating a defect type.

History is kept: a PAK with sessions (`pak_in_use`), a batch with sessions
(`batch_in_use`) and a defect group referenced by a check or a step
(`defect_group_in_use`) cannot be deleted; archive them instead.

Administrators, managers and engineers read sessions and the check catalog
(`verification.read`).
