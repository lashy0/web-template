# Request validation

The frontend generates zod schemas from the OpenAPI document and builds its
forms on them, so a rule the frontend should check before sending belongs in
the schema, not only in code.

## Field types

A request field is typed with an `Annotated` alias that carries
`msgspec.Meta` constraints: `min_length`, `max_length`, `pattern`, `ge`.
msgspec checks them while decoding the request body, and they appear in the
OpenAPI schema:

```python
Title = Annotated[str, msgspec.Meta(min_length=1, max_length=NAME_MAX_LENGTH)]


class ProductionOrderCreate(CamelizedBaseStruct):
    name: Title
    description: Description | None = None
```

Shared aliases live next to the rules they describe: `Login`, `PersonName` and
`Password` in `app/lib/validation.py`, `Title` and `Description` in
`app/domain/production/schemas/_common.py`, `Title`, `Text` and `CODE_ALLOWED`
in `app/domain/quality/schemas/_common.py`.

A pattern must mean the same in Python and JavaScript: no inline flags such as
`(?i)`, no `\Z`, no named groups. A pattern accepts the input the backend
normalizes, such as an upper-case login, not only the normalized value.

## `__post_init__`

The `validate_*` functions in `__post_init__` stay: they normalize the value
(strip whitespace, lower the case) and apply the rules a schema cannot express,
such as reserved logins or repeated characters. They also run for structs built
in code, for example by the `otk users create` command, which msgspec does not
check.

## Errors

A value that breaks a `Meta` constraint is rejected by Litestar with 400 and a
list of field errors in `extra`; a rule from `__post_init__` gives 400 with a
`detail`. See `docs/errors.md`.

The PAK machine API keeps its lenient checks in `__post_init__` (a blank unit
means none), since PAKs are not built on the generated schemas.
