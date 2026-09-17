from app.config import KratosSettings
from app.lib.kratos import KratosClient


def provide_kratos_client(
    settings: KratosSettings,
) -> KratosClient:
    return KratosClient(
        base_url=settings.admin_url,
        timeout=settings.admin_timeout,
        concurrency=settings.admin_concurrency,
    )
