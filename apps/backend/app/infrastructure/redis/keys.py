from app.core.config import Settings

RedisKeyPart = str | int


def build_redis_key(
    settings: Settings,
    *parts: RedisKeyPart,
) -> str:
    prefix = settings.REDIS_PREFIX.strip(":")

    if not prefix:
        raise ValueError("REDIS_PREFIX must contain characters other than ':'")

    if not parts:
        raise ValueError("At least one Redis key part is required")

    serialized_parts = tuple(str(part) for part in parts)
    if any(not part for part in serialized_parts):
        raise ValueError("Redis key parts must not be empty")

    return ":".join((prefix, *serialized_parts))
