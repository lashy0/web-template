from enum import StrEnum


class KgPermission(StrEnum):
    READ = "kg:read"

    PREFIX_READ = "kg:prefix:read"
    PREFIX_CREATE = "kg:prefix:create"
    PREFIX_UPDATE = "kg:prefix:update"
    PREFIX_DELETE = "kg:prefix:delete"
