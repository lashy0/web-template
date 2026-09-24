# Errors

Services report failures by raising exceptions. `app.lib.exceptions` turns
them into HTTP responses; handlers do not build error responses themselves.

## Response body

Every error response has the Litestar shape, documented in OpenAPI as
`ErrorResponse`:

```json
{
  "status_code": 409,
  "detail": "Archived production order cannot be modified.",
  "extra": { "code": "production_order_archived" }
}
```

- `detail` is a human-readable message. It may be reworded at any time;
  clients must not parse it.
- `extra.code` is present only for errors that define a code. The code is the
  contract: clients branch on it, so it is never renamed or reused for a
  different condition. Remove a code only together with the condition.
- Server errors (5xx) never carry a code or the original detail outside debug
  mode, so SQL fragments and upstream responses do not reach the client.

Request validation errors produced by Litestar keep their own shape: `extra` is
a list of field errors there.

## Status codes

The base class decides the status:

| Base class | Status |
|---|---|
| `NotFoundError` (Advanced Alchemy), `ApplicationNotFoundError` | 404 |
| `ApplicationConflictError`, `IntegrityError` (Advanced Alchemy) | 409 |
| `AuthenticationError` | 401 |
| `AuthorizationError` | 403 |
| other `ApplicationClientError` | 400 |
| `ServiceUnavailableError` | 503 |
| anything else | 500 |

A conflict caused by a database error other than a constraint violation (lost
connection, deadlock, serialization failure) becomes 500, not 409: the whole
cause chain is inspected. Keep the cause when translating a database error:

```python
try:
    pak = await self.create(data, auto_commit=False)
except IntegrityError as error:
    raise PakDeviceCodeTakenError from error
```

## Where errors are declared

- **An error with a code is a class in the domain's `exceptions.py`**
  (`app/domain/<domain>/exceptions.py`). The module is the list of codes the
  domain promises to clients. The class sets `code` and a default `detail`:

  ```python
  class ProductionOrderArchivedError(ApplicationConflictError):
      code = "production_order_archived"
      detail = "Archived production order cannot be modified."
  ```

  A call site may pass a more specific `detail`, never a different `code`.

- **An error without a code is raised in place** with a generic class:
  `NotFoundError("Production order not found.")`,
  `RepositoryError(...)` for invariant violations that indicate a bug.
  404 needs no code: the status already says what happened.

- **Errors of an external system or a pure library** live next to its client
  in `app/lib/<name>/exceptions.py` (`kratos`, `hydra`, `lorawan`). They follow
  the same rule: a code only where clients must distinguish the condition.

Give a code when a client has to react to the condition differently from
other failures with the same status: a conflict the UI explains to the user,
a refused action the UI hides. Do not give codes to server errors.

## Naming

- Class: `<Subject><Condition>Error`, for example `PakDeviceArchivedError`,
  `LastAdministratorError`.
- Code: the same in `snake_case`, prefixed with the subject:
  `pak_device_archived`, `production_order_archived`. Codes are unique across
  the application.

## Tests

Assert the exception class, not the message or the code string:
`pytest.raises(ProductionOrderArchivedError)`. The class already fixes the code.
