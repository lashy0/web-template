import sys
import urllib.error
import urllib.request

HEALTHCHECK_URL = "http://127.0.0.1:8000/api/health/live"


def main() -> None:
    try:
        with urllib.request.urlopen(HEALTHCHECK_URL, timeout=5) as response:
            if response.status != 200:
                raise RuntimeError(f"Unexpected status code: {response.status}")
    except (urllib.error.URLError, TimeoutError, RuntimeError):
        sys.exit(1)


if __name__ == "__main__":
    main()
