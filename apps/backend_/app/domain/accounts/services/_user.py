from __future__ import annotations

from advanced_alchemy.extensions.litestar import repository, service

from app.db import models as m
from app.lib.deps import CompositeServiceMixin


class UserService(CompositeServiceMixin, service.SQLAlchemyAsyncRepositoryService[m.User]):
    """Handles database operations for users."""

    class Repo(repository.SQLAlchemyAsyncRepository[m.User]):
        """User SQLAlchemy Repository."""
        model_type = m.User

    repository_type = Repo
