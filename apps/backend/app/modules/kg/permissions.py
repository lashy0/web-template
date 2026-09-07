from enum import StrEnum


class KgPermission(StrEnum):
    READ = "kg:read"

    PREFIX_READ = "kg:prefix:read"
    PREFIX_CREATE = "kg:prefix:create"
    PREFIX_UPDATE = "kg:prefix:update"
    PREFIX_ARCHIVE = "kg:prefix:archive"
    PREFIX_DELETE = "kg:prefix:delete"

    VERSION_READ = "kg:version:read"
    VERSION_CREATE = "kg:version:create"
    VERSION_UPDATE = "kg:version:update"
    VERSION_ARCHIVE = "kg:version:archive"
    VERSION_DELETE = "kg:version:delete"
