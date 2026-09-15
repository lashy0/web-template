from enum import StrEnum


class UserPermission(StrEnum):
    READ = "user:read"
    CREATE = "user:create"
    UPDATE = "user:update"
    SET_PASSWORD = "user:set_password"
    SET_ACTIVE = "user:set_active"
    ARCHIVE = "user:archive"
    DELETE = "user:delete"
