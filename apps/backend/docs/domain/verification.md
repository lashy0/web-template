# Verification (OTK)

A PAK verifies a KG unit by running a series of checks on it. The PAK reports
each run as a **verification session** made of **steps**, one step per check.
Users only read the history; PAKs write it through the machine API.

## Reading

| Request | Route |
|---|---|
| history, filtered and paged (by `batchIdIn`, `devEuiIn`, `pakIdIn`, `pakKindIn`, `statusIn`, start time) | `GET /verification/sessions` |
| one session with its steps | `GET /verification/sessions/{id}` |
| state of a PAK's slots | `GET /verification/sessions/by-slot?pakId=…&finishedWithin=…` |

The state of a slot is the session it runs, or the one it finished last, with
the number, check label and status of every step started so far; steps not
started yet are only counted in `totalSteps`, since a PAK names a check when it
starts it. A
finished session stays the state of its slot for `finishedWithin` seconds (0 by
default, so only running sessions are returned); after that the slot is left
out, as a slot that never ran a session is. A session the system closed as
`incomplete` is never a slot's state: by then the PAK has stopped reporting it
for a long time or has moved on. The server knows only what PAKs report: a
slot without a running session may still hold a KG unit.

Every report of a PAK, and every session the system closes, publishes the
realtime event `verification.changed` with the `pakId` and `batchId` of the
sessions that changed, once per pair; see [realtime events](../realtime.md).
Opening a session may close one on another PAK, so one report can announce two
PAKs. A session ended on an OTK-line PAK also publishes `batch.changed`: it may
have set the unit's OTK status.

## Machine API

PAKs call `/machine/pak`, `/machine/kg/units` and `/machine/verification/sessions` with a Hydra access token
(`Authorization: Bearer ...`, client credentials of the PAK's OAuth client).
Browser sessions do not apply there. An inactive or archived PAK gets 403.

The PAK gets the token at `POST /machine/token`: OAuth2 client credentials,
`grant_type=client_credentials` as a form with `Authorization: Basic
base64(client_id:access_key)`. Traefik sends that path straight to Hydra, so
the backend has no handler for it, and its errors follow OAuth2
(`{error, error_description}`), not the API format. The token lives an hour;
on 401 the PAK gets a new one and repeats the request once. See the
[identity infrastructure](../../../../infrastructure/identity/README.md).

| Request | Route |
|---|---|
| read its own registration, to show it | `GET /machine/pak` → `{code, kind}` |
| read what to write into a unit | `GET /machine/kg/units/{devEui}/keys` → `{devEui, keys, multicast}` |
| open a session | `POST /machine/verification/sessions` `{devEui, slotNo, firmwareVersion, totalSteps}` |
| start a step | `POST /machine/verification/sessions/{id}/steps` `{stepNo, checkName, checkLabel, defectGroupCode}` |
| report a step | `PUT /machine/verification/sessions/{id}/steps/{stepNo}` `{status: passed\|failed, measurementValue, measurementMin, measurementMax, measurementUnit}` |
| finish a session | `POST /machine/verification/sessions/{id}/complete` `{status: passed\|failed\|aborted}` |

A PAK reads its registration when it starts and after each new token. A kind
changed in between reaches it in the `pakKind` of the next session it opens.

Before verifying a unit the PAK reads its keys. `keys` has one shape per
activation of the batch, told apart by `scheme`, with the fields the PAK
writes; ABP units also get the AppKey and JoinEUI, as PAKs have written them
so far:

| `scheme` | Fields |
|---|---|
| `otaa-1.0` | `joinEui` (the AppEUI), `appKey` |
| `otaa-1.1` | `joinEui`, `appKey`, `nwkKey` |
| `abp-1.0` | `devAddr`, `nwkSKey`, `appSKey`, `appKey`, `joinEui` |
| `abp-1.1` | `devAddr`, `fNwkSIntKey`, `sNwkSIntKey`, `nwkSEncKey`, `appSKey`, `appKey`, `joinEui` |

`multicast` lists both [multicast groups](multicast.md) of the batch by
`groupId`, each with `mcAddr`, `mcNwkSKey`, `mcAppSKey`, `frequencyHz` and
`datarate`. Hex values are lower case. The keys are refused as opening a
session would be (unknown, scrapped or packed unit, archived batch; see
below), except that a session of the unit running elsewhere is decided when
the session opens. The response is `Cache-Control: no-store` and not audited.

`firmwareVersion` is the KG controller firmware the PAK flashes, such as
`v.1.0.9` (`controller_version` in the old system), not the KG version. The
KG version comes from the unit's batch: a session shows it as `kgVersion`,
or `null` when the batch has none.

Every request may be repeated after a lost response: the same report is
answered with the current state, a different one with a 409. A session of
another PAK answers 404.

## Sessions

A KG unit and a PAK slot each have at most one `running` session.

| Opening a session when | Result |
|---|---|
| the unit is unknown | `verification_kg_not_found` |
| the unit is scrapped | `verification_kg_scrapped` |
| the unit is packed or shipped and the PAK is an OTK-line PAK | `verification_kg_packed`; an engineering PAK may verify it |
| the unit's batch is archived | `verification_batch_archived`; a completed batch may be verified |
| the unit already runs in the same slot | that session is resumed |
| the unit runs in another slot, reported within the last 60 minutes | `verification_session_already_running` |
| the unit runs in another slot, idle longer | that session is closed as `incomplete`, a new one starts |
| the slot runs another unit | that session is closed as `incomplete`: the PAK moved on |

A session ends `passed`, `failed` or `aborted` when the PAK finishes it, and
`incomplete` when the system closes it. `passed` needs every step passed; a
running step blocks `passed` and `failed` (`verification_session_incomplete`)
and is aborted with the session on `aborted`; when the system closes a session,
its running step ends `incomplete` too. A PAK reports steps only `passed` or
`failed`. `lastActivityAt` is the PAK's last report; closing a session as
incomplete keeps it. `completedSteps` counts
the steps reported `passed` or `failed`, out of `totalSteps`, to show progress.

A PAK may abort a session after the system has already closed it: `aborted`
on an `incomplete` session is answered with the session as it is, not a 409,
because both mean the PAK did not finish it. `passed` or `failed` on it is
still `verification_session_not_running`.

The background task `expire_stale_verification_sessions` runs every minute and
closes sessions idle for `BACKEND_VERIFICATION_SESSION_TTL_MINUTES` (120) as
incomplete, with their running step, and announces the change. The 60 minutes above are
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

Packing needs `otkStatus` `passed` and no running OTK-line session; see
[packing](packing.md).

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
