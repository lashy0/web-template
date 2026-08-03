# Scripts

Scripts for managing the Traefik infrastructure.

## Available scripts

### `deploy.py`

Runs the development or production Traefik stack with Docker Compose. See the
[Traefik README](../README.md) for configuration details.

Requirements:

* Docker with the Compose plugin
* uv

Run the development stack from the repository root:

```console
uv run --script infrastructure/traefik/scripts/deploy.py up dev
```

Run the production stack:

```console
uv run --script infrastructure/traefik/scripts/deploy.py up prod
```

Show service status or stop the selected environment:

```console
uv run --script infrastructure/traefik/scripts/deploy.py status dev
uv run --script infrastructure/traefik/scripts/deploy.py down dev
```
