# Tests

## Running tests

Run from `apps/pak-simulator`:

```console
uv run pytest tests/unit                  # simulator behavior
uv run pytest tests/unit/test_client.py   # one file
uv run pytest tests/integration           # exported OpenAPI contract
uv run pytest                            # full suite; no external services
uv run pytest --cov                      # full suite with the coverage gate
```

The coverage gate is 90% and is intended for the full suite.
Neither backend nor Docker is required.

## Unit or integration

| | `tests/unit` | `tests/integration` |
|---|---|---|
| Tests | configuration, client, simulation, CLI and terminal behavior | simulator wire contracts against `packages/api-client/openapi.json` |
| Boundary | `MockTransport` for HTTP; `AsyncMock` for `VerificationClient` | the exported OpenAPI document |
| External services | none | none |

## Layout

- **Paths mirror the module under test:** `config/`, `simulation/`,
  `application/`, `cli/` and `terminal/`.
- **Name files after the simulator code:** `client.py` has
  `test_client.py` and `test_client_retries.py`; `preflight.py` has
  `test_preflight.py`.
- **Every test directory has an `__init__.py`.**
- **Fixtures live in the nearest `conftest.py`.** Shared setup belongs in
  `tests/unit/conftest.py`; small helpers in `support.py`.

## Writing a test

- **One behavior per test.** Arrange, act, assert, separated by blank lines.
  Name the case `test_<action>_<outcome>`.
- **Test through the public entry point.** Check results, exceptions and
  observable state. Parameterize cases with the same shape.
- **Mock only the boundary.** Test the real `PakClient` with explicit HTTP
  responses. Simulation tests use the real planner, queue and executor with
  an injected client mock. Do not recreate backend session rules.
- **Check client calls when they are the behavior:** request payloads, session
  completion, cleanup order or absence of network access.
- **Check CLI exit codes and the expected diagnostic together.**
- **Use a fresh client per test.** Coordinate concurrent tests with events,
  bound waits with `TEST_TIMEOUT`, and use `running_task` for background tasks.
  Inject sleep or clock dependencies instead of waiting in real time.
- **Mark modules:** `unit` or `integration`; async modules also add `anyio`.
