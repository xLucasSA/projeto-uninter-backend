from collections.abc import Iterable
from datetime import datetime
from typing import cast

from sqlalchemy import Table, and_, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from raizes_api.application.ports.catalogo import Movimentacao
from raizes_api.domain.catalogo.catalogo import OfertaNaUnidade, Unidade
from raizes_api.domain.compartilhado.dinheiro import Dinheiro
from raizes_api.infrastructure.db.modelos import (
    CardapioUnidadeModel,
    EstoqueModel,
    MovimentacaoEstoqueModel,
    ProdutoModel,
    UnidadeModel,
)

ORIGEM_API = "API"


class RepositorioCatalogoSql:
    def __init__(self, sessao: AsyncSession) -> None:
        self._sessao = sessao

    async def obter_unidade(self, unidade_id: int) -> Unidade | None:
        linha = (
            await self._sessao.execute(
                select(UnidadeModel.id, UnidadeModel.codigo, UnidadeModel.ativa).where(
                    UnidadeModel.id == unidade_id
                )
            )
        ).one_or_none()
        return Unidade(id=linha.id, codigo=linha.codigo, esta_ativa=linha.ativa) if linha else None

    async def ofertas(self, unidade_id: int, produto_ids: Iterable[int]) -> dict[int, OfertaNaUnidade]:
        consulta = (
            select(
                ProdutoModel.id,
                ProdutoModel.nome,
                ProdutoModel.ativo,
                CardapioUnidadeModel.preco,
                CardapioUnidadeModel.ativo.label("cardapio_ativo"),
                CardapioUnidadeModel.disponivel_de,
                CardapioUnidadeModel.disponivel_ate,
            )
            .outerjoin(
                CardapioUnidadeModel,
                and_(
                    CardapioUnidadeModel.produto_id == ProdutoModel.id,
                    CardapioUnidadeModel.unidade_id == unidade_id,
                ),
            )
            .where(ProdutoModel.id.in_(list(produto_ids)))
        )
        return {
            linha.id: OfertaNaUnidade(
                produto_id=linha.id,
                nome_produto=linha.nome,
                produto_ativo=linha.ativo,
                preco=Dinheiro(linha.preco) if linha.preco is not None else None,
                cardapio_ativo=bool(linha.cardapio_ativo),
                disponivel_de=linha.disponivel_de,
                disponivel_ate=linha.disponivel_ate,
            )
            for linha in await self._sessao.execute(consulta)
        }


class RepositorioEstoqueSql:
    def __init__(self, sessao: AsyncSession) -> None:
        self._sessao = sessao

    async def reservar(
        self, unidade_id: int, produto_id: int, quantidade: int, agora: datetime
    ) -> int | None:
        # Sem SELECT antes: o UPDATE condicional é atômico; o CHECK (quantidade >= 0) é a última defesa.
        resultado = await self._sessao.execute(
            update(EstoqueModel)
            .where(
                EstoqueModel.unidade_id == unidade_id,
                EstoqueModel.produto_id == produto_id,
                EstoqueModel.quantidade >= quantidade,
            )
            .values(quantidade=EstoqueModel.quantidade - quantidade, atualizado_em=agora)
            .returning(EstoqueModel.quantidade)
            .execution_options(synchronize_session=False)
        )
        return resultado.scalar_one_or_none()

    async def devolver(self, unidade_id: int, produto_id: int, quantidade: int, agora: datetime) -> int:
        resultado = await self._sessao.execute(
            update(EstoqueModel)
            .where(EstoqueModel.unidade_id == unidade_id, EstoqueModel.produto_id == produto_id)
            .values(quantidade=EstoqueModel.quantidade + quantidade, atualizado_em=agora)
            .returning(EstoqueModel.quantidade)
            .execution_options(synchronize_session=False)
        )
        return resultado.scalar_one()

    async def saldo(self, unidade_id: int, produto_id: int) -> int:
        quantidade = await self._sessao.scalar(
            select(EstoqueModel.quantidade).where(
                EstoqueModel.unidade_id == unidade_id, EstoqueModel.produto_id == produto_id
            )
        )
        return quantidade or 0

    async def registrar_movimentacoes(self, movimentacoes: Iterable[Movimentacao]) -> None:
        linhas = [
            {
                "unidade_id": movimentacao.unidade_id,
                "produto_id": movimentacao.produto_id,
                "tipo": movimentacao.tipo.value,
                "origem": ORIGEM_API,
                "quantidade": movimentacao.quantidade,
                "saldo_apos": movimentacao.saldo_apos,
                "pedido_id": movimentacao.pedido_id,
            }
            for movimentacao in movimentacoes
        ]
        if not linhas:
            return
        # Um único INSERT ... VALUES (...), (...): sem RETURNING e sem buscar o próximo id antes.
        # O api_app só tem INSERT em movimentacao_estoque; RETURNING exigiria SELECT, e nextval() exigiria
        # USAGE na sequence. O id vem do default da coluna identity, que não pede esse privilégio.
        await self._sessao.execute(insert(cast(Table, MovimentacaoEstoqueModel.__table__)).values(linhas))
