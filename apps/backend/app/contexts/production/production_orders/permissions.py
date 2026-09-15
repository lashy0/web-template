from enum import StrEnum


class ProductionOrderPermission(StrEnum):
    CREATE = "production_order:create"
    READ = "production_order:read"
    UPDATE = "production_order:update"
    ARCHIVE = "production_order:archive"
    DELETE = "production_order:delete"
