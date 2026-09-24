from __future__ import annotations

from advanced_alchemy.extensions.litestar import repository, service

from app.db import models as m


class KgUnitService(service.SQLAlchemyAsyncRepositoryService[m.KgUnit]):
    """Read access to the KG units registered by batches.

    Units change only through production processes, never directly by a user.
    """

    class Repo(repository.SQLAlchemyAsyncRepository[m.KgUnit]):
        """KG unit SQLAlchemy repository."""

        model_type = m.KgUnit
        id_attribute = "dev_eui"

    repository_type = Repo
