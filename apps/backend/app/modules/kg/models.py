"""Compatibility re-exports; KG persistence is owned by production.kg."""

from app.contexts.production.kg.model import (
    KG_STATE_DB_TYPE,
    KgDevEuiPrefix,
    KgState,
    KgUnit,
    KgVersion,
    LoRaWanCredentials,
)

__all__ = ["KG_STATE_DB_TYPE", "KgDevEuiPrefix", "KgState", "KgUnit", "KgVersion", "LoRaWanCredentials"]


# Compatibility exports: prefix/version ownership is app.contexts.production.kg.model.
