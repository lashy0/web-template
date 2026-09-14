"""Compatibility import for the shipment repository moved to production."""

from app.contexts.production.shipments.repository import ShipmentRepository

BatchShipmentRepository = ShipmentRepository

__all__ = ["BatchShipmentRepository"]
