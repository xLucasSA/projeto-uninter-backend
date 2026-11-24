import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from raizes_api.domain.fidelidade.lancamento import LancamentoFidelidade, TipoLancamento
from raizes_api.infrastructure.db.modelos import LancamentoFidelidadeModel


class RepositorioFidelidadeSql:
    """Append-only: lançamentos nunca são alterados nem apagados (guideline 04)."""

    def __init__(self, sessao: AsyncSession) -> None:
        self._sessao = sessao

    async def adicionar(self, lancamento: LancamentoFidelidade) -> None:
        # UNIQUE (pedido_id, tipo) é a última defesa contra um segundo crédito para o mesmo pedido.
        self._sessao.add(
            LancamentoFidelidadeModel(
                id=lancamento.id,
                cliente_id=lancamento.cliente_id,
                pedido_id=lancamento.pedido_id,
                tipo=lancamento.tipo.value,
                pontos=lancamento.pontos,
                criado_em=lancamento.criado_em,
            )
        )
        await self._sessao.flush()

    async def credito_do_pedido(self, pedido_id: uuid.UUID) -> LancamentoFidelidade | None:
        modelo = await self._sessao.scalar(
            select(LancamentoFidelidadeModel).where(
                LancamentoFidelidadeModel.pedido_id == pedido_id,
                LancamentoFidelidadeModel.tipo == TipoLancamento.CREDITO.value,
            )
        )
        if modelo is None:
            return None
        return LancamentoFidelidade(
            id=modelo.id,
            cliente_id=modelo.cliente_id,
            pedido_id=modelo.pedido_id,
            tipo=TipoLancamento(modelo.tipo),
            pontos=modelo.pontos,
            criado_em=modelo.criado_em,
        )
