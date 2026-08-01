# Scripts

Repository-level scripts for development, maintenance and deployment.

## Available scripts

### `deploy.py`

Deploys the production stack with Docker Compose. See the
[deployment guide](../docs/deployment.md) for configuration and image tag details.

Requirements:

* Docker with the Compose plugin
* Git
* uv

Run the deployment from the repository root:

```console
uv run --script scripts/deploy.py
```
