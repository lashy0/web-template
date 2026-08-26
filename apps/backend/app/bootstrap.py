import asyncio

from loguru import logger

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.infrastructure.database.session import create_database
from app.infrastructure.kratos.client import KratosIdentityManager
from app.modules.users.service import UserManagementService


async def bootstrap() -> None:
    settings = get_settings()
    setup_logging(settings)
    database = create_database(settings)
    try:
        service = UserManagementService(
            database.session_factory,
            KratosIdentityManager(settings),
        )
        user = await service.bootstrap_first_administrator(
            name=settings.BOOTSTRAP_ADMIN_NAME,
            login=settings.BOOTSTRAP_ADMIN_LOGIN,
            password_loader=settings.bootstrap_admin_password,
        )
        if user is None:
            logger.info("First-administrator bootstrap skipped because users already exist")
        else:
            logger.info("First-administrator bootstrap completed")
    finally:
        await database.close()
        await logger.complete()


if __name__ == "__main__":
    asyncio.run(bootstrap())
