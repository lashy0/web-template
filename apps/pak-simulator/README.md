# PAK simulator

Simulates PAKs checking KG units and sends sessions and check results to the
backend. Use it to check the API and the application's verification screens
without physical equipment.

Show the installed version with `uv run pak-sim --version` (or `-V`). The version
comes from the installed package metadata, built from `[project].version` in
`pyproject.toml`.

## First run

You need `uv`, a running backend, and a PAK and KG units created in the application.

From the repository root:

```powershell
cd apps/pak-simulator
Copy-Item scenarios/.env.example scenarios/.env
```

Open `scenarios/.env` and fill in these three groups:

| Group | What to enter |
|---|---|
| **Backend** | The address of your running application |
| **PAK** | The code, client ID and access key from the PAK card in the application |
| **KG units** | The first DevEUI and the number of consecutive units from your batch |

Example `.env` file — replace the PAK values and unit range with your own:

```dotenv
# Backend
PAK_SIM_SERVER=http://localhost

# PAK — copy these values from its card in the application
PAK1_CODE=PAK-01
PAK1_CLIENT_ID=your-client-id
PAK1_ACCESS_KEY=your-access-key

# KG units — choose an existing range from your batch
PAK1_DEV_EUI_FROM=0016C00003000001
PAK1_DEV_EUI_COUNT=10
```

Here, the unit range is **10 units**, from `0016C00003000001` through
`0016C0000300000A`. These units must already exist in the application.

Check the configuration, server and credentials, then start:

```powershell
uv run pak-sim check scenarios/demo.yaml
uv run pak-sim run scenarios/demo.yaml --once
```

`check` does not create verification sessions. To check the configuration without
connecting to the backend, add `--offline`.

**Use `--once` to process the queue and finish. Without it, the queue repeats
until you stop the simulator.**

The demo runs six slots independently. Each free slot takes the next unit;
failed units are not retested.

## Settings

Edit `.env` for the connection, PAK credentials and unit selection. Edit
[scenarios/demo.yaml](scenarios/demo.yaml) for the verification settings.
See [the scenario guide](scenarios/README.md) for the YAML format and examples.

| Setting | Where | Demo value |
|---|---|---|
| First unit | `.env`: `PAK1_DEV_EUI_FROM` | Your batch's first DevEUI |
| Unit count | `.env`: `PAK1_DEV_EUI_COUNT` | Your batch size |
| Slots | YAML: `paks[].slots` | `6` |
| Pass probability | YAML: `profiles.kg-v3.pass_rate` | `0.8` (80%) |
| First session delay per slot | YAML: `sessions.start` | `0s..2s` |
| Delay between sessions on a slot | YAML: `sessions.swap` | `1s..3s` |

`pass_rate: 1` makes all completed verifications pass; `0` makes them all fail.
`0.8` is a probability per session, not an exact 80% of every batch.

You can override settings for one run without editing files:

| CLI option | Effect |
|---|---|
| `--speed 5` | Run checks and delays five times faster; default is `1` |
| `--pass-rate 0.5` | Set a 50% probability of passing |
| `--start-delay 0s..2s` | Set the initial delay for each slot |
| `--session-delay 1s..3s` | Set the delay between sessions |
| `--log` | Print events instead of the live table |
| `--pak PAK-01` | Run only a selected PAK; repeat to select several |

`--server` replaces the YAML address before environment expansion, so its original
variable can be unset. With `--pak`, only selected PAK settings and their profiles
are expanded and validated. PAK codes must still be available to identify entries.

The unit count is set in the configuration, not through CLI.

Example: run the configured units once, five times faster, with a 50% pass chance:

```powershell
uv run pak-sim run scenarios/demo.yaml --once --speed 5 --pass-rate 0.5
```

See all options with `uv run pak-sim run --help`.

## Reading the screen

Each PAK has its own progress and results:

```text
Units: 7/20 processed · 6 running · 7 queued
Run summary: Passed 5 · Failed 2 · Actual pass rate: 71%
```

| Label | Meaning |
|---|---|
| `processed` | Units already handled, including skips and API errors |
| `running` | Units currently being checked |
| `queued` | Units waiting to start, including those waiting between sessions |
| `Passed` / `Failed` | Completed verification results |
| `Actual pass rate` | Passed sessions divided by passed plus failed sessions |
| `Error` | A connection or API problem |
| `Cleanup errors` | Failed requests to abort open sessions; excluded from attempt counts |
| `Internal errors` | Unexpected failures that stop a PAK; excluded from attempt counts |
| `Recent events` | The last eight events, shared by all selected PAKs |
| `Finished` | This PAK's run ended; its units may have passed or failed |

`Next session in 0:02` is a slot's countdown before starting the next unit.
`Simulation complete` appears when all selected PAKs finish.

An authentication or access error stops the affected PAK. Its unfinished units
remain queued in the run and are not counted as processed; other PAKs continue.
Fix the credentials or PAK status, then start a new run. Queue state is not saved
between launches. Connection, API and session cleanup errors make the simulator
exit with code `1`, even when the queue has been exhausted. Failed verification
checks are expected simulation outcomes and do not fail the simulator itself.

An unexpected internal error also stops only the affected PAK. Its slots stop,
open sessions are aborted, and unfinished units remain unprocessed. Other PAKs
continue; with `--once`, the command waits for them and then exits with code `1`.
In loop mode, they keep running until you stop the simulator. Internal failures
are shown in the PAK's alert and totals; the full diagnostic traceback is logged
to stderr. Capture stderr if you need to keep diagnostics after the run.
Cancellation still stops every PAK and exits with code `130`, even if session
cleanup fails. Errors in shared event output or live rendering stop the whole run.

If opening a unit resumes a previous session, the simulator restarts it when it
already has completed steps, or its firmware version or step count differs from
the current profile. A session with zero completed steps and matching parameters
can be reused. If its first step was already started with another check, the
simulator aborts it and restarts once with the same plan and attempt number.
A repeated conflict or a conflict on a later step is reported as an API error.

Token and verification requests use Tenacity to retry connection failures and HTTP 502, 503 and
504 up to four times, waiting 0.5, 1, 2 and 4 seconds between attempts. Rejected
credentials are not retried. A rejected verification token is renewed once.
Renewing a token does not reset the verification request's remaining retry budget.
Idle independent slots wait for queue changes through `asyncio.Event`.

With `--seed`, check outcomes, measurements and interruptions are reproducible
for the same PAK code, DevEUI, queue cycle and attempt. HTTP response timing can
change slot assignment and event order, but does not change these generated
results. Retest decisions have their own stream; scheduling delays use separate
streams for each slot.

## Stopping

Press `Ctrl+C`. The simulator sends requests to abort its current open sessions
and exits with code `130`; SIGTERM uses the same cleanup path. Sessions already
superseded by another unit in their slot are not kept in the cleanup queue.

## Development

Run checks from `apps/pak-simulator`:

```console
uv run ruff check .
uv run ruff format --check .
uv run mypy src tests
uv run pytest tests/unit
uv run pytest
uv run pytest --cov
```

Dependencies are split into `linting` and `test` groups; `dev` includes both,
as in the backend. See [tests/README.md](tests/README.md) for the test layout.

The implementation is split into:

- `config/scenario.py`: loading and conversion into simulation objects, preserving shared profiles.
- `config/environment.py`: Pydantic settings sources, file precedence and lazy scalar references.
- `config/yaml_loader.py`: YAML parsing, PAK selection and substitution with cycle and collision checks.
- `config/spec.py`: Pydantic models, field and reference validation, and the Draft 2020-12 editor schema.
- `config/spans.py`: time and measurement range parsing, also used by CLI overrides.
- `config/overrides.py`: delay and pass probability overrides; shared profiles stay shared.
- `config/errors.py`: scenario errors and credential-safe validation diagnostics.
- `values.py`, `model.py`: value objects and compiled simulation models.
- `contracts.py`, `client.py`: typed machine API shapes and OAuth/HTTP client.
- `application.py`: client lifetime and concurrent execution, independent of terminal output.
- `simulation/queue.py`: reservations, progress and retest routing.
- `simulation/retests.py`: seeded decisions about whether and where to retest a unit.
- `simulation/statistics.py`: typed attempt counts and immutable snapshots with shared total calculations.
- `simulation/reporting.py`: result handling, slot updates and operator-facing events.
- `simulation/session.py`: attempt preparation and cleanup, plan execution with one conflict recovery,
  and confirmed session opening/completion for each slot.
- `simulation/runner.py`: independent or synchronized slot scheduling, with explicit stop reasons.
- `simulation/state.py`: attempt outcomes, runtime state, results and immutable UI snapshots.
- `terminal/live.py`: screen updates from immutable snapshots on the simulation's event loop.
- `terminal/`, `cli.py`: rendering, command options, signals and exit codes.

Package `__init__.py` files expose the public entry points through `__all__`:

```python
from pak_simulator import PakClient, Simulation, SimulationExecution, open_simulation_run
from pak_simulator.config import RunOptionError, ScenarioError, configure_run, load, schema
from pak_simulator.simulation import EventLog, PakRun, PakSnapshot, RunResult
from pak_simulator.terminal import format_event, render, run_live, show_scenario
```

Implementation modules import their dependencies directly to keep the package
entry points out of internal dependency chains.
