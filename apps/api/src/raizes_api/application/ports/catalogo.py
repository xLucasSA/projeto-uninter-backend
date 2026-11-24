import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from raizes_api.domain.catalogo.catalogo import OfertaNaUnidade, TipoMovimentacao, Unidade


class RepositorioCatalogo(Protocol):
    """Leitura forte do catálogo para validar comandos (o read model pode estar atrasado)."""

    async def obter_unidade(self, unidade_id: int) -> Unidade | None: ...

    async def ofertas(self, unidade_id: int, produto_ids: Iterable[int]) -> dict[int, OfertaNaUnidade]:
        """Uma oferta por produto existente; produto inexistente fica fora do dicionário."""
        ...


@dataclass(frozen=True, slots=True)
class Movimentacao:
    """`quantidade` com sinal: negativa na saída do pedido, positiva no estorno."""

    tipo: TipoMovimentacao
    unidade_id: int
    produto_id: int
    quantidade: int
    saldo_apos: int
    pedido_id: uuid.UUID


class RepositorioEstoque(Protocol):
    async def reservar(
        self, unidade_id: int, produto_id: int, quantidade: int, agora: datetime
    ) -> int | None:
        """Baixa atômica, sem leitura prévia. Retorna o saldo após a baixa, ou None se não havia saldo."""
        ...

    async def devolver(self, unidade_id: int, produto_id: int, quantidade: int, agora: datetime) -> int:
        """Estorno atômico (`quantidade = quantidade + q`). Retorna o saldo após a devolução."""
        ...

    async def saldo(self, unidade_id: int, produto_id: int) -> int: ...

    async def registrar_movimentacoes(self, movimentacoes: Iterable[Movimentacao]) -> None: ...
