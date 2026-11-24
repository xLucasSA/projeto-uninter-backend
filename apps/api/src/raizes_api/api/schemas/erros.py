from datetime import datetime

from pydantic import Field

from raizes_api.api.schemas.base import SchemaBase


class DetalheErroResponse(SchemaBase):
    field: str = Field(examples=["itens[0].quantidade"])
    issue: str = Field(examples=["Disponível: 1"])


class ErroResponse(SchemaBase):
    """Formato único de todas as falhas da API."""

    error: str = Field(examples=["ESTOQUE_INSUFICIENTE"])
    message: str = Field(examples=["Não há quantidade suficiente para um ou mais itens."])
    details: list[DetalheErroResponse] = Field(default_factory=list)
    timestamp: datetime
    path: str = Field(examples=["/pedidos"])
    request_id: str | None = Field(default=None, examples=["7c1d0b9e-4f2a-4a7e-9a51-2a3f1c9d8e10"])
