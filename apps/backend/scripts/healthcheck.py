"""Container liveness: the API process answers its health endpoint.

``/api/health`` answers 503 while PostgreSQL, Kratos or Hydra is down. That
is readiness of the dependencies, not of this process, so 503 counts as alive
here; otherwise an Ory outage would mark the API unhealthy and Traefik would
stop routing to it.
"""

import sys
import urllib.error
import urllib.request

HEALTHCHECK_URL = "http://127.0.0.1:8000/api/health"
ALIVE_STATUSES = {200, 503}


def main() -> None:
    try:
        with urllib.request.urlopen(HEALTHCHECK_URL, timeout=5) as response:
            status = response.status
    except urllib.error.HTTPError as error:
        status = error.code
    except (urllib.error.URLError, TimeoutError):
        sys.exit(1)

    if status not in ALIVE_STATUSES:
        sys.exit(1)


if __name__ == "__main__":
    main()
