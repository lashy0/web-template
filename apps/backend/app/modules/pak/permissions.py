from enum import StrEnum


class PakPermission(StrEnum):
    CREATE = "pak:create"
    READ = "pak:read"
    UPDATE = "pak:update"
    SET_ACTIVE = "pak:set_active"
    ARCHIVE = "pak:archive"
    READ_ACCESS_KEY = "pak:read_access_key"
    ROTATE_ACCESS_KEY = "pak:rotate_access_key"
    DELETE = "pak:delete"
