from advanced_alchemy.extensions.litestar import SQLAlchemyPlugin

from app import config
from app.utils.domain import DomainPlugin

alchemy = SQLAlchemyPlugin(config=config.alchemy)
domain = DomainPlugin()
