import argparse
import json
from pathlib import Path
from typing import Literal, cast

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.routing import APIRoute, iter_route_contexts

from app.main import create_app

Audience = Literal["web", "machine"]

AUDIENCE_TAGS: dict[Audience, frozenset[str]] = {
    "web": frozenset(
        {
            "audit",
            "auth",
            "batch",
            "defects",
            "kg",
            "pak",
            "users",
            "verification",
        }
    ),
    "machine": frozenset({"pak-machine", "verification-machine"}),
}


def export_openapi(app: FastAPI, output: Path, audience: Audience) -> None:
    """Write the OpenAPI document for ``audience`` to ``output``."""
    audience_tags = AUDIENCE_TAGS[audience]
    routes = [
        route_context
        for route_context in iter_route_contexts(app.routes)
        if isinstance(route_context.original_route, APIRoute)
        and audience_tags.intersection(route_context.tags)
    ]
    tags = [tag for tag in app.openapi_tags or [] if tag["name"] in audience_tags]
    schema = get_openapi(
        title=app.title,
        version=app.version,
        openapi_version=app.openapi_version,
        summary=app.summary,
        description=app.description,
        routes=routes,
        tags=tags or None,
        servers=app.servers,
        terms_of_service=app.terms_of_service,
        contact=app.contact,
        license_info=app.license_info,
        separate_input_output_schemas=app.separate_input_output_schemas,
        external_docs=app.openapi_external_docs,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(schema, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def parse_arguments() -> tuple[Path, Audience]:
    parser = argparse.ArgumentParser(
        description="Export a backend OpenAPI document for an API audience.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Destination for the OpenAPI JSON document.",
    )
    parser.add_argument(
        "--audience",
        choices=("web", "machine"),
        required=True,
        help="API audience to export.",
    )
    arguments = parser.parse_args()

    return cast(Path, arguments.output), cast(Audience, arguments.audience)


def main() -> None:
    output, audience = parse_arguments()
    export_openapi(create_app(), output, audience)


if __name__ == "__main__":
    main()
