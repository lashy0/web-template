"""Compatibility alias; credentials now belong to production.kg."""

from app.contexts.production.kg.credentials import KgCredentials as LoRaWanCredentialsService

__all__ = ["LoRaWanCredentialsService"]
