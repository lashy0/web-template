def normalize_trimmed(value: object) -> object:
    if isinstance(value, str):
        return value.strip()

    return value
