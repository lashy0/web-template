"""OpenAPI documentation of error and paginated responses."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import msgspec
from advanced_alchemy.service import OffsetPagination
from litestar.openapi.datastructures import ResponseSpec
from litestar.openapi.spec import OpenAPIType, Schema
from litestar.params import KwargDefinition
from litestar.plugins import OpenAPISchemaPlugin
from litestar.typing import FieldDefinition

if TYPE_CHECKING:
    from litestar._openapi.schema_generation import SchemaCreator


class ErrorExtra(msgspec.Struct):
    """Machine-readable details of an application error."""

    code: str


class ErrorResponse(msgspec.Struct):
    """Body of every error response (``litestar.exceptions.responses``).

    ``extra`` is present only for application errors that define a stable code.
    """

    status_code: int
    detail: str
    extra: ErrorExtra | None = None


_DESCRIPTIONS = {
    401: "Authentication is missing or invalid.",
    403: "The authenticated user lacks the required permission or may not act on this target.",
    404: "The resource does not exist.",
    409: "The request conflicts with the current state of the resource.",
    503: "An identity provider required by the request is unavailable.",
}


def error_responses(*status_codes: int) -> dict[int, ResponseSpec]:
    """Describe error responses for a route handler's ``responses`` argument."""
    return {
        status_code: ResponseSpec(
            data_container=ErrorResponse,
            description=_DESCRIPTIONS[status_code],
            generate_examples=False,
        )
        for status_code in status_codes
    }


class OffsetPaginationSchemaPlugin(OpenAPISchemaPlugin):
    """Describe ``OffsetPagination[Item]`` as the component ``ItemPage``.

    Litestar names the component after the item's module path, and its own
    pagination plugin, which inlines the page without required fields, takes
    over when ``litestar.pagination`` is imported before Advanced Alchemy, as
    the CLI does.
    """

    def is_plugin_supported_field(self, field_definition: FieldDefinition) -> bool:
        return field_definition.origin is OffsetPagination

    def to_openapi_schema(self, field_definition: FieldDefinition, schema_creator: SchemaCreator) -> Schema:
        (item,) = field_definition.inner_types
        name = f"{item.annotation.__name__}Page"
        page = FieldDefinition.from_annotation(
            field_definition.annotation,
            kwarg_definition=KwargDefinition(schema_component_key=name),
        )
        component = schema_creator.create_component_schema(
            page,
            required=["items", "limit", "offset", "total"],
            property_fields={},
            title=name,
        )
        component.properties = {
            "items": Schema(type=OpenAPIType.ARRAY, items=schema_creator.for_field_definition(item)),
            "limit": Schema(type=OpenAPIType.INTEGER),
            "offset": Schema(type=OpenAPIType.INTEGER),
            "total": Schema(type=OpenAPIType.INTEGER),
        }
        # A schema returned here is inlined; the reference points at the component.
        return cast("Schema", schema_creator.schema_registry.get_reference_for_field_definition(page))


__all__ = ("ErrorExtra", "ErrorResponse", "OffsetPaginationSchemaPlugin", "error_responses")
