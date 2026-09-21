# Backend instructions

Litestar + Advanced Alchemy backend. Read this file before making changes.

## Commands

Run from `apps/backend_`:

- `uv run pytest tests/unit` — fast, no external services
- `uv run pytest` — full suite (Docker Desktop required: Postgres + Kratos)
- `uv run ruff check . --fix && uv run ruff format .`
- `uv run mypy .` and `uv run basedpyright`
- `uv run alembic revision --autogenerate -m "..."` / `uv run alembic upgrade head`
- `uv run app --help` — Litestar CLI (`app.__main__:run_cli`)
