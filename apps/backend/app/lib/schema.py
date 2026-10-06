import msgspec
from advanced_alchemy.utils.text import camelize
from pydantic import BaseModel as _BaseModel
from pydantic import ConfigDict


class BaseStruct(msgspec.Struct):
    """Base of request and response structs; ``advanced_alchemy.service.schema_dump`` turns one into a dict."""


class CamelizedBaseStruct(BaseStruct, rename="camel"):
    """Camelized Base Struct"""


class Message(CamelizedBaseStruct):
    message: str


class BaseSchema(_BaseModel):
    """Base Settings."""

    model_config = ConfigDict(
        validate_assignment=True,
        from_attributes=True,
        use_enum_values=True,
        arbitrary_types_allowed=True,
    )


class CamelizedBaseSchema(BaseSchema):
    """Camelized Base pydantic schema."""

    model_config = ConfigDict(populate_by_name=True, alias_generator=camelize)
