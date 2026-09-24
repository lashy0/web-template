"""Application dependency providers generators."""

from __future__ import annotations

import inspect
from typing import Any

from advanced_alchemy.extensions.litestar.providers import (
    create_service_dependencies as _create_service_dependencies,
)
from advanced_alchemy.extensions.litestar.providers import (
    create_service_provider,
)
from litestar.di import Provide

__all__ = (
    "create_service_dependencies",
    "create_service_provider",
)


def create_service_dependencies(
    service_class: type[Any],
    /,
    **kwargs: Any,
) -> dict[str, Provide]:
    """Create service dependencies compatible with Litestar 2.24's explicit DI.

    Advanced Alchemy 1.11 builds the dynamic ``filters`` provider with an
    explicit ``__signature__``, but leaves its ``__annotations__`` implicit.
    Litestar 2.24 reads the latter while validating dependencies, which emits
    deprecation warnings and would break under Litestar 3. This adapter keeps
    the generated annotations in sync with the provider signature.
    """
    dependencies = _create_service_dependencies(service_class, **kwargs)
    filters = dependencies.get("filters")

    if filters is not None:
        provider = filters.dependency
        signature = inspect.signature(provider)
        annotations = dict(getattr(provider, "__annotations__", {}))
        annotations.update(
            {
                name: parameter.annotation
                for name, parameter in signature.parameters.items()
                if parameter.annotation is not inspect.Parameter.empty
            }
        )
        provider.__annotations__ = annotations

    return dependencies
