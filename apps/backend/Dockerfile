# Builder stage
FROM ghcr.io/astral-sh/uv:0.11.32-python3.13-trixie AS builder

ENV \
    # Compile bytecode
    # Ref: https://docs.astral.sh/uv/guides/integration/docker/#compiling-bytecode
    UV_COMPILE_BYTECODE=1 \
    # uv Cache
    # Ref: https://docs.astral.sh/uv/guides/integration/docker/#caching
    UV_LINK_MODE=copy \
    UV_NO_DEV=1 \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app/backend

# Ref: https://docs.astral.sh/uv/guides/integration/docker/#intermediate-layers
# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

# Copy application code
COPY . .


# Runtime stage
FROM python:3.13-slim-trixie AS runtime

ENV \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/backend/.venv/bin:$PATH"

# Setup a non-root user
RUN groupadd --system --gid 451 nonroot \
    && useradd --system --uid 451 --gid 451 --create-home nonroot

WORKDIR /app/backend

COPY --from=builder \
    --chown=nonroot:nonroot \
    /app/backend \
    /app/backend

ARG BACKEND_VERSION=dev
ENV BACKEND_VERSION="${BACKEND_VERSION}"

ENTRYPOINT []

USER nonroot
