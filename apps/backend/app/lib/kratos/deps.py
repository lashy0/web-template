from litestar.di import NamedDependency

from app.config import KratosSettings
from app.lib.kratos import KratosClient


def provide_kratos_client(kratos_settings: NamedDependency[KratosSettings]) -> KratosClient:
    return KratosClient(
        base_url=kratos_settings.admin_url,
        timeout=kratos_settings.admin_timeout,
        concurrency=kratos_settings.admin_concurrency,
    )
