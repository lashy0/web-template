# Scenario configuration

A scenario describes which PAKs to run, which KG units to verify, and what checks
to send to the backend. Start with [demo.yaml](demo.yaml): copy it, change the
settings, and keep the schema comment on the first line for editor hints.

See [the main README](../README.md) for setup, running and stopping the simulator.

Pydantic validates the scenario after environment substitution. The editor schema
uses JSON Schema Draft 2020-12 and accepts `${NAME}` references for the server,
DevEUIs, batch count, times and values. References between profiles, checks and
PAKs are checked when the scenario is loaded.

Repeated keys in a YAML mapping are rejected with their line and column instead
of silently using the last value. Keys that become identical after environment
expansion are also rejected, with their original names and location in the
configuration. YAML anchors and `<<` merges remain supported; local settings may
override values inherited from a merge. An alias may be reused, but references
that form a cycle are rejected as configuration errors.

## File structure

| Block | Purpose |
|---|---|
| `server` | Backend address |
| `sessions` | Slot scheduling, delays, interruptions and retests |
| `paks` | PAK credentials, slots, profile and unit selection |
| `profiles` | Ordered checks, pass probability and possible defects |

A small complete example:

```yaml
# yaml-language-server: $schema=../scenario.schema.json

server: ${PAK_SIM_SERVER}

sessions:
  loading: independent
  start: 0s..2s
  swap: 1s..3s
  abandon: 0
  retest:
    chance: 0

paks:
  - code: "${PAK1_CODE}"
    client_id: ${PAK1_CLIENT_ID}
    access_key: ${PAK1_ACCESS_KEY}
    profile: basic
    slots: 6
    dev_eui:
      from: "${PAK1_DEV_EUI_FROM}"
      count: ${PAK1_DEV_EUI_COUNT}

profiles:
  basic:
    firmware_version: "v.1.0.9"
    pass_rate: 0.8
    checks:
      - name: Flash
        label: Прошивка КГ
        group: ОБ
        value: 1
        time: 24s..26s
        critical: true
```

## Connection and environment

Set connection values and unit selection in `.env` next to the scenario.
See [the main README](../README.md#first-run) for the initial setup.
`${NAME}` in scalar values and mapping keys is replaced after YAML parsing and before validation.
Quotes, `#` and newlines in credentials remain part of their value. System
environment variables take priority over the scenario's `.env`, which takes
priority over `.env` in the working directory. Loading a scenario does not
modify the process environment.

`pydantic-settings` loads the files and merges their values with the caller's
environment. A scenario-specific source keeps `${NAME}` literal during file
loading, so only references needed by the selected PAKs are resolved. Settings
are loaded afresh for every scenario; changes to `.env` take effect on the next load.

Referenced `.env` values are expanded recursively; unused entries are ignored.
Missing variables,
including nested references such as `SECRET=prefix-${MISSING}`, produce a
configuration error naming the missing variable. An explicitly empty value is
kept empty; required fields still reject blank values.

`--server` replaces the configured address before expansion, including when the
original address variable is missing. `run --pak CODE` selects entries before
expanding their settings and profiles, so other PAKs can remain unconfigured.
Codes of all entries must be resolvable for selection. A plain `check` validates
the entire scenario.

Keep DevEUIs quoted, including `from`, so YAML reads them as strings.
Keep numeric placeholders such as `count: ${PAK1_DEV_EUI_COUNT}` unquoted.

| Setting | Default |
|---|---|
| `server` | Required; for example, `http://localhost` |
| `verify_tls` | `true` |

The server address must include `http://` or `https://` and a host. Save YAML
and `.env` files using UTF-8 encoding. Times, values and limits must be finite
numbers; `NaN` and infinity are rejected. Required text fields must not be blank.

Like a real PAK, the simulator knows only the application address: it gets
tokens at `<server>/api/machine/token` and reports under `<server>/api/machine/`.

## Session scheduling

These settings apply to every PAK in the scenario.

```yaml
sessions:
  loading: independent
  start: 0s..2s
  swap: 1s..3s
  abandon: 0
  retest:
    chance: 0
```

| Setting | Meaning | Default when omitted |
|---|---|---|
| `loading` | `independent`: each free slot takes the next unit. `together`: wait for the whole load to finish before loading the next units. | `independent` |
| `start` | Delay before the first session on each slot. With `together`, applied at the start of every load. | `0s..15s` |
| `swap` | Delay between units on a slot, or between loads with `together`. | `8s..20s` |
| `abandon` | Probability of interrupting a session partway through; `0` disables it. | `0` |

Retests are optional behavior for failed units:

| `retest` setting | Meaning | Default when omitted |
|---|---|---|
| `chance` | Probability of another attempt after a failed session; `0` disables retests. | `0.5` |
| `max_attempts` | Maximum attempts per unit, including the first. | `3` |
| `other_slot` | Probability of moving the retest to another slot in `independent` mode; ignored with one slot or `together`. | `0.5` |
| `pause` | Delay before a retest on the same slot. A retest on another slot uses that slot's normal delay. | `5s..15s` |

**Keep `retest.chance: 0` for a run without retests.** Removing the entire `retest`
block uses the defaults above and enables them. The demo also sets
`max_attempts: 1`; `other_slot` and `pause` have no effect while retests are disabled.

## PAKs and KG units

Each entry in `paks` needs `code`, `client_id`, `access_key`, `profile` and
`dev_eui`. Copy credentials from the PAK card in the application. PAK codes and
OAuth `client_id` values must be unique. `profile` must match a key in `profiles`.

`slots` is the number of parallel slots: from `1` to `32`, default `6`.
PAKs and KG units must already exist in the application.

Select consecutive DevEUIs:

```yaml
dev_eui:
  from: "0016C00003000001"
  count: 10
```

This selects ten units, ending at `0016C0000300000A`. `count` must be a positive
integer. Alternatively, list individual units:

```yaml
dev_eui:
  - "0016C00003000001"
  - "0016C0000300000A"
```

Each DevEUI must contain 16 hexadecimal digits.

For a second PAK, add another entry to `paks` and its variables to `.env`:

```yaml
  - code: "${PAK2_CODE}"
    client_id: ${PAK2_CLIENT_ID}
    access_key: ${PAK2_ACCESS_KEY}
    profile: kg-v3
    slots: 6
    dev_eui:
      from: "${PAK2_DEV_EUI_FROM}"
      count: ${PAK2_DEV_EUI_COUNT}
```

PAKs can share a profile. Their unit selections must not overlap; conflicts are
rejected after DevEUIs are normalized, including overlaps between ranges and lists.

## Profiles and checks

Each profile needs `firmware_version` and a nonempty `checks` list.
Checks run in the order written in YAML.

`pass_rate` controls the probability of a passed session: `1` makes every
completed verification pass, `0` makes every one fail, and `0.8` gives each
session an 80% pass chance. It does not guarantee an exact share in a small batch.
If omitted or `null`, defects and measurement limits determine the result.

Example measurement check:

```yaml
- name: TestCurrentSensor
  label: Проверка датчика тока
  group: СИ
  time: 3.9s..4.3s
  value: 203.33..231.00
  unit: mA
  limits: [135, 240]
```

| Check field | Meaning |
|---|---|
| `name`, `label`, `group` | Required check name, display label and defect group code |
| `time` | Required duration or duration range |
| `value` | Optional reported number or numeric range |
| `unit` | Optional measurement unit |
| `limits` | Optional `[minimum, maximum]`, inclusive; use `null` for an unbounded side |
| `critical` | `true` stops the session if this check fails; default `false` |

A check without limits passes unless a defect changes it. `[0, 0]` is treated
as no limits. With `pass_rate` set, generated check results are adjusted to match
the chosen session outcome.
Forced failures use a finite measurement outside the limits. If no finite
out-of-bounds value exists, the failed check reports a missing measurement instead.

## Times and values

| Type | Examples |
|---|---|
| Duration | `2` (seconds), `2s`, `500ms`, `1.5m` |
| Random duration | `0s..2s`, `500ms..1s` |
| Value | `1`, `-90`, `203.33` |
| Random value | `1990..2064`, `203.33..231.00`, `-77..-56` |

Ranges are sampled independently. Write the smaller endpoint first.
Value ranges preserve the decimal precision written in their endpoints.

## Defects

The optional `defects` block describes how failed checks can look:

```yaml
defects:
  current_out_of_range:
    chance: 0.1
    steps:
      TestCurrentSensor: 40..130

  flash_failed:
    chance: 0.02
    steps:
      Flash:
        value: 0
        time: 120s..130s
        status: failed
```

| Defect field | Meaning | Default |
|---|---|---|
| `chance` | Required probability of the defect, from `0` to `1` | — |
| `steps` | Required changes by check name or exact label | — |
| `persists` | Probability that an existing defect remains on a retest | `1` |
| `transient` | Roll the defect again for each session, ignoring `persists` | `false` |

A step can be a replacement value or a block with `value`, `time`, `name`,
`label` and `status` (`passed` or `failed`). Unset fields keep the check's values.
Use the exact label to target one check when several share a name, such as
different dimming levels.

When `pass_rate` is set, it chooses the session result and defects provide
failure details; `chance` does not set the overall failure rate.
