"""Compatibility schema exports while public API ownership moves with KG."""

from app.modules.kg.schemas import (
    CreateKgDevEuiPrefixRequest,
    CreateKgVersionRequest,
    DevEuiPrefix,
    KgDevEuiPrefixListResponse,
    KgDevEuiPrefixResponse,
    KgVersionListResponse,
    KgVersionResponse,
    UpdateKgDevEuiPrefixArchivedRequest,
    UpdateKgDevEuiPrefixRequest,
    UpdateKgVersionArchivedRequest,
    UpdateKgVersionRequest,
)

__all__ = [
    "CreateKgDevEuiPrefixRequest",
    "CreateKgVersionRequest",
    "DevEuiPrefix",
    "KgDevEuiPrefixListResponse",
    "KgDevEuiPrefixResponse",
    "KgVersionListResponse",
    "KgVersionResponse",
    "UpdateKgDevEuiPrefixArchivedRequest",
    "UpdateKgDevEuiPrefixRequest",
    "UpdateKgVersionArchivedRequest",
    "UpdateKgVersionRequest",
]
