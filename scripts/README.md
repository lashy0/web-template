# Scripts

Repository-level scripts for development, maintenance and deployment.

## Available scripts

### `deploy.py`

Deploys the production stack. It uses `uv version` to read the backend version
from `apps/backend/pyproject.toml`, uses it as the shared backend image tag, and
starts Docker Compose.

Requirements:

* Docker with the Compose plugin
* uv

Run the deployment from the repository root:

```console
uv run --script scripts/deploy.py
```
