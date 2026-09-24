# Tests

## Running tests

Run from `apps/backend_`:

```console
uv run pytest tests/unit                  # no external services
uv run pytest path/to/test_file.py        # one file
uv run pytest                             # full suite; needs Docker Desktop
```

Integration tests start the containers they need (PostgreSQL and external
services) themselves.

## Unit or integration

| | `tests/unit` | `tests/integration` |
|---|---|---|
| External services | none | real PostgreSQL and external services in Docker |
| Tests | pure logic: validation, policies, guards, response parsing, error mapping, middleware | services, repositories, transactions, routes that touch the database |
| Doubles | `MagicMock`, `AsyncMock`, `patch` at the boundary | none, except a small fake that fails on purpose |

A service that writes to the database or calls an external service is tested
only in `tests/integration`. Mocking its session or client would test the
mocks, not the commit order described in `docs/transactions.md`.

## Layout

- **The test path mirrors the code path.** `app/lib/validation.py` is tested in
  `tests/unit/lib/test_validation.py`; `app/domain/<domain>/services/_<name>.py`
  in `tests/integration/<domain>/services/test_<name>_service.py`.
- **Name the file after the module under test**, not after the external service
  it calls.
- **Every test directory has an `__init__.py`.** Pytest imports test modules by
  package path, so two files may share a name in different directories.
- **Fixtures live in the nearest `conftest.py`.** Fixtures of one domain go in
  `tests/integration/<domain>/conftest.py`; shared ones in `tests/conftest.py`
  or `tests/integration/conftest.py`.

## Writing a test

- **One behavior per test.** A test has one action and checks its outcome.
  Several steps of a scenario are several tests.
- **The name states the case:** `test_<action>_<outcome>`, for example
  `test_last_administrator_cannot_be_demoted` or
  `test_exception_to_http_response_not_found`. A failing test name should tell
  what broke without opening the file.
- **Arrange, act, assert**, separated by blank lines. No `if` or `for` in a
  test body; a test that needs a branch is two tests.
- **Test through the public entry point**: the service method, the dependency
  provider, the route. Private helpers are tested directly only when they are
  the boundary with an external SDK, such as response parsing or error mapping.
- **Cover each code branch once.** Use one representative per branch, not every
  class that reaches it: one not-found error for the 404 branch, not every
  not-found exception in the project.
- **Keep `parametrize` for two to four cases of the same shape.** A long table of
  inputs and expected results is hard to read and hides which case matters.
- **Check types and statuses, not message texts.** `pytest.raises(ValidationError)`
  and `response.status_code == 409` survive rewording; `match="..."` does not.
  Match a message only when the text is part of the API contract.
- **Prefer a little duplication to a clever helper.** A helper or fixture is
  worth it when the same setup repeats across several tests and its name says
  what it prepares (`create_user(role=UserRole.ADMINISTRATOR)`). A helper that
  decides what to call or what to expect hides the test.
- **Do not test what does not exist yet.** A dependency that no route uses is
  tested when the route appears, through that route.

```python
async def test_last_administrator_cannot_be_demoted(user_service: UserService, create_user: CreateUser) -> None:
    administrator = await create_user(role=UserRole.ADMINISTRATOR)

    with pytest.raises(ApplicationConflictError):
        await user_service.assign_role(administrator.id, UserRole.MANAGER)
```

## Test doubles

- **Prefer the real thing.** Real implementation first, then a small fake, then
  a mock.
- **Mock only at the boundary**: the incoming request, the database session in a
  unit test, the SDK of an external service. Never mock the code under test or a
  service it calls.
- **Assert outcomes, not calls.** Check the returned value, the raised
  exception or the stored state. `assert_awaited_*` is right only when the call
  is the behavior itself, for example that an external service was not
  contacted.
- **A fake that fails on purpose is a small class** with the methods the test
  needs, not a configured mock.

```python
def test_exception_to_http_response_not_found() -> None:
    request = MagicMock()
    request.app.debug = False

    with patch("app.lib.exceptions.create_exception_response") as mock_create:
        exception_to_http_response(request, NotFoundError("not found"))

    assert isinstance(mock_create.call_args.args[1], NotFoundException)
```

## Fixtures and markers

- **Mark the module, not each test:**
  `pytestmark = [pytest.mark.anyio, pytest.mark.integration, pytest.mark.services]`.
  Every module is marked `unit` or `integration`; async modules add `anyio`.
- **Request only the fixtures a test uses.** `session` already depends on
  `db_cleanup`; do not add `db_cleanup` to a test that takes `session`.
- **External services keep their data between tests.** Database tables are
  emptied after each test, data in external services is not, so the
  identifiers stored there (logins, client IDs) must be unique. Generate them
  with a random suffix.
- **Commit through `unit_of_work`** in integration tests, as CLI commands and
  jobs do. Effects registered with `after_commit` or `on_rollback` run only when
  the block exits.

## Differences from litestar-fullstack

The test suite started from the
[litestar-fullstack](https://github.com/litestar-org/litestar-fullstack/tree/main/src/py/tests)
tests and keeps their shape. It differs where they are wrong:

- **Health returns 503**, not 500, when a dependency is offline: the service is
  unavailable, not broken.
- **Controller discovery is tested against the real `app.domain`**, not only
  with mocked modules. Discovery skips modules that fail to import, so only a
  real run notices a controller that silently disappeared.

## Further reading

- [Litestar: Testing](https://docs.litestar.dev/latest/usage/testing.html)
- [pytest: Good Integration Practices](https://docs.pytest.org/en/stable/explanation/goodpractices.html)
- [Software Engineering at Google, ch. 12: Unit Testing](https://abseil.io/resources/swe-book/html/ch12.html)
- [Software Engineering at Google, ch. 13: Test Doubles](https://abseil.io/resources/swe-book/html/ch13.html)
