from litestar.di import NamedDependency

from app.config import HydraSettings
from app.lib.hydra.client import HydraClient


def provide_hydra_client(
    hydra_settings: NamedDependency[HydraSettings],
) -> HydraClient:
    return HydraClient(
        base_url=hydra_settings.admin_url,
        timeout=hydra_settings.admin_timeout,
        concurrency=hydra_settings.admin_concurrency,
    )
