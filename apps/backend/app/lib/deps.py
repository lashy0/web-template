"""Application dependency providers generators."""

from __future__ import annotations

import inspect
from typing import Annotated, Any, cast, get_origin

from advanced_alchemy.extensions.litestar.providers import (
    DEPENDENCY_DEFAULTS,
    DependencyDefaults,
    FilterConfig,
    create_service_provider,
)
from advanced_alchemy.extensions.litestar.providers import (
    create_filter_dependencies as _create_filter_dependencies,
)
from advanced_alchemy.extensions.litestar.providers import (
    create_service_dependencies as _create_service_dependencies,
)
from litestar.di import NamedDependency, Provide
from litestar.params import SkipValidation

# Validation of filter values is skipped, so their type does not matter to Litestar.
type _FilterDependency = NamedDependency[SkipValidation[Any]]

__all__ = (
    "create_filter_dependencies",
    "create_service_dependencies",
    "create_service_provider",
)


def create_service_dependencies(
    service_class: type[Any],
    /,
    **kwargs: Any,
) -> dict[str, Provide]:
    """Create service dependencies compatible with Litestar 2.24's explicit DI.

    Their filter dependencies use the same annotation adapter as
    :func:`create_filter_dependencies`.
    """
    return _mark_filter_dependencies(
        _create_service_dependencies(service_class, **kwargs),
        kwargs.get("dep_defaults", DEPENDENCY_DEFAULTS),
    )


def create_filter_dependencies(
    config: FilterConfig,
    dep_defaults: DependencyDefaults = DEPENDENCY_DEFAULTS,
) -> dict[str, Provide]:
    """Create only filter dependencies, keeping the service provider on its owning layer."""
    return _mark_filter_dependencies(_create_filter_dependencies(config, dep_defaults), dep_defaults)


def _mark_filter_dependencies(
    dependencies: dict[str, Provide],
    dep_defaults: DependencyDefaults,
) -> dict[str, Provide]:
    """Mark dynamic filter parameters as explicit dependencies for Litestar 2.24.

    Advanced Alchemy 1.11 builds the dynamic ``filters`` provider with an
    explicit ``__signature__``, but leaves its ``__annotations__`` implicit.
    Litestar 2.24 reads the latter while validating dependencies, which emits
    deprecation warnings and would break under Litestar 3. This adapter keeps
    the generated annotations in sync with the provider signature.

    The same release leaves the ``in_fields`` filter parameters unmarked, so
    Litestar would infer them as dependencies; they are marked here like the
    other generated filters.
    """
    filters = dependencies.get(dep_defaults.FILTERS_DEPENDENCY_KEY)

    if filters is not None:
        provider = filters.dependency
        signature = inspect.signature(provider)
        signature = signature.replace(
            parameters=[
                parameter.replace(annotation=_FilterDependency.__value__)
                if parameter.annotation is not inspect.Parameter.empty
                and get_origin(parameter.annotation) is not Annotated
                else parameter
                for parameter in signature.parameters.values()
            ]
        )
        cast("Any", provider).__signature__ = signature
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
