"""Compatibility access point for production KG credential persistence."""

from app.contexts.production.kg.repository import KgRepository as LoRaWanCredentialsRepository

__all__ = ["LoRaWanCredentialsRepository"]
