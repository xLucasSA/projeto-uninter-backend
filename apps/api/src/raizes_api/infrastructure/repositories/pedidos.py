import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from raizes_api.domain.compartilhado.atores import TipoAtor
from raizes_api.domain.compartilhado.canais import CanalPedido
from raizes_api.domain.compartilhado.dinheiro import Dinheiro
from raizes_api.domain.pedidos.pedido import Autoria, ItemPedido, MudancaDeStatusPedido, Pedido
from raizes_api.domain.pedidos.status import StatusPedido
from raizes_api.infrastructure.db.modelos import HistoricoStatusPedidoModel, ItemPedidoModel, PedidoModel


class RepositorioPedidosSql:
    def __init__(self, sessao: AsyncSession) -> None:
        self._sessao = sessao

    async def adicionar(self, pedido: Pedido) -> None:
        self._sessao.add(
            PedidoModel(
                id=pedido.id,
                unidade_id=pedido.unidade_id,
                cliente_id=pedido.cliente_id,
                canal_pedido=pedido.canal.value,
                status=pedido.status.value,
                total=pedido.total.valor,
                criado_por_tipo=pedido.criado_por.tipo.value,
                criado_por_id=pedido.criado_por.id,
                observacao=pedido.observacao,
                criado_em=pedido.criado_em,
                atualizado_em=pedido.atualizado_em,
            )
        )
        await self._sessao.flush()
        self._sessao.add_all(
            ItemPedidoModel(
                pedido_id=pedido.id,
                produto_id=item.produto_id,
                nome_produto=item.nome_produto,
                quantidade=item.quantidade,
                preco_unitario=item.preco_unitario.valor,
                subtotal=item.subtotal.valor,
            )
            for item in pedido.itens
        )
        self._sessao.add(
            HistoricoStatusPedidoModel(
                pedido_id=pedido.id,
                status_anterior=None,
                status_novo=pedido.status.value,
                ator_tipo=pedido.criado_por.tipo.value,
                ator_id=pedido.criado_por.id,
                ocorrido_em=pedido.criado_em,
            )
        )
        await self._sessao.flush()

    async def obter_para_atualizacao(self, pedido_id: uuid.UUID) -> Pedido | None:
        modelo = await self._sessao.scalar(
            select(PedidoModel)
            .where(PedidoModel.id == pedido_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if modelo is None:
            return None
        itens = await self._sessao.scalars(
            select(ItemPedidoModel).where(ItemPedidoModel.pedido_id == pedido_id).order_by(ItemPedidoModel.id)
        )
        return Pedido(
            id=modelo.id,
            unidade_id=modelo.unidade_id,
            canal=CanalPedido(modelo.canal_pedido),
            status=StatusPedido(modelo.status),
            itens=tuple(
                ItemPedido(
                    produto_id=item.produto_id,
                    nome_produto=item.nome_produto,
                    quantidade=item.quantidade,
                    preco_unitario=Dinheiro(item.preco_unitario),
                )
                for item in itens
            ),
            cliente_id=modelo.cliente_id,
            criado_por=Autoria(tipo=TipoAtor(modelo.criado_por_tipo), id=modelo.criado_por_id),
            observacao=modelo.observacao,
            criado_em=modelo.criado_em,
            atualizado_em=modelo.atualizado_em,
        )

    async def registrar_mudanca(self, pedido: Pedido, mudanca: MudancaDeStatusPedido) -> None:
        await self._sessao.execute(
            update(PedidoModel)
            .where(PedidoModel.id == pedido.id)
            .values(status=pedido.status.value, atualizado_em=pedido.atualizado_em)
            .execution_options(synchronize_session=False)
        )
        self._sessao.add(
            HistoricoStatusPedidoModel(
                pedido_id=pedido.id,
                status_anterior=mudanca.status_anterior.value,
                status_novo=mudanca.status_novo.value,
                ator_tipo=mudanca.autoria.tipo.value,
                ator_id=mudanca.autoria.id,
                motivo=mudanca.motivo,
                ocorrido_em=mudanca.ocorrido_em,
            )
        )
        await self._sessao.flush()
