# Backend instructions (`apps/backend_`)

Run backend commands from `apps/backend_`.

## Documentation

Before changing backend behavior, consult the relevant guide in `docs/`.

## Tests and checks

Before writing or changing tests, read `tests/README.md`.

- `uv run pytest tests/unit` — fast unit tests; no external services.
- `uv run pytest path/to/test_file.py` — run a targeted test file.
- `uv run pytest` — full suite; requires Docker Desktop with Postgres and
  Kratos.
- `uv run ruff check .` — lint.
- `uv run ruff format --check .` — check formatting without changing files.
- `uv run mypy .` and `uv run basedpyright` — type checks.
- `uv run app --help` — show available Litestar CLI commands.

To apply Ruff fixes, use `uv run ruff check . --fix` and `uv run ruff format .`;
these commands modify files.

## Database migrations

- Create a revision with `uv run alembic revision --autogenerate -m "..."`.
  Equivalent CLI command: `uv run app database make-migrations`.
- Apply revisions with `uv run alembic upgrade head`. Equivalent CLI command:
  `uv run app database upgrade`.
- Revisions are tracked in the `ddl_version` table. Tests create tables with
  `metadata.create_all` and do not detect missing migrations. After changing a
  model, run `uv run alembic upgrade head && uv run alembic check` against the
  intended development database.
