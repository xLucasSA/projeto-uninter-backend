from collections.abc import Sequence
from typing import Any, Self

from pydantic import Field

from raizes_api.api.schemas.base import SchemaBase
from raizes_api.application.paginacao import Pagina


class PaginaResponse[T](SchemaBase):
    """Envelope de toda listagem paginada."""

    items: list[T]
    page: int = Field(examples=[1])
    limit: int = Field(examples=[10])
    total: int = Field(
        description="Total de itens com os filtros aplicados, em todas as páginas.", examples=[57]
    )

    @classmethod
    def de(cls, pagina: Pagina[Any], itens: Sequence[T]) -> Self:
        return cls(items=list(itens), page=pagina.pagina, limit=pagina.limite, total=pagina.total)
