from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class SchemaBase(BaseModel):
    """Contratos JSON em camelCase (guideline 05); em Python, os campos seguem snake_case."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        validate_by_name=True,
        validate_by_alias=True,
        serialize_by_alias=True,
    )
