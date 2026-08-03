# Scripts

Repository-level scripts for development, maintenance and deployment.

## Available scripts

### `deploy.py`

Runs the development or production stack with Docker Compose. See the
[deployment guide](../docs/deployment.md) for production configuration and image
tag details.

Requirements:

* Docker with the Compose plugin
* Git
* uv

Run the development stack with file watching from the repository root:

```console
uv run --script scripts/deploy.py up dev
```

Build and run the production stack in the background:

```console
uv run --script scripts/deploy.py up prod
```

Show service status or stop the selected environment:

```console
uv run --script scripts/deploy.py status dev
uv run --script scripts/deploy.py down dev
```
