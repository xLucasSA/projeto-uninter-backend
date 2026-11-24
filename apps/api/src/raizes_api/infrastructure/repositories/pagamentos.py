import uuid

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from raizes_api.application.ports.pagamentos import WebhookRecebido
from raizes_api.domain.compartilhado.dinheiro import Dinheiro
from raizes_api.domain.pagamentos.pagamento import STATUS_ATIVOS, FormaPagamento, Pagamento, StatusPagamento
from raizes_api.infrastructure.db.modelos import PagamentoModel, WebhookRecebidoModel


class RepositorioPagamentosSql:
    def __init__(self, sessao: AsyncSession) -> None:
        self._sessao = sessao

    async def adicionar(self, pagamento: Pagamento) -> None:
        # O índice único parcial (um PENDENTE/APROVADO por pedido) é a última defesa; o bloqueio do pedido
        # já impede duas solicitações simultâneas.
        self._sessao.add(
            PagamentoModel(
                id=pagamento.id,
                pedido_id=pagamento.pedido_id,
                status=pagamento.status.value,
                forma=pagamento.forma.value,
                valor=pagamento.valor.valor,
                tentativas=pagamento.tentativas,
                solicitado_em=pagamento.solicitado_em,
            )
        )
        await self._sessao.flush()

    async def obter(self, pagamento_id: uuid.UUID) -> Pagamento | None:
        # populate_existing: depois do bloqueio do pedido, a releitura precisa vir do banco, não da sessão.
        modelo = await self._sessao.scalar(
            select(PagamentoModel)
            .where(PagamentoModel.id == pagamento_id)
            .execution_options(populate_existing=True)
        )
        return _pagamento(modelo) if modelo else None

    async def ativo_do_pedido(self, pedido_id: uuid.UUID) -> Pagamento | None:
        modelo = await self._sessao.scalar(
            select(PagamentoModel).where(
                PagamentoModel.pedido_id == pedido_id,
                PagamentoModel.status.in_([status.value for status in STATUS_ATIVOS]),
            )
        )
        return _pagamento(modelo) if modelo else None

    async def atualizar(self, pagamento: Pagamento) -> None:
        await self._sessao.execute(
            update(PagamentoModel)
            .where(PagamentoModel.id == pagamento.id)
            .values(
                status=pagamento.status.value,
                transacao_externa_id=pagamento.transacao_externa_id,
                motivo_recusa=pagamento.motivo_recusa,
                tentativas=pagamento.tentativas,
                concluido_em=pagamento.concluido_em,
            )
            .execution_options(synchronize_session=False)
        )


class RepositorioWebhooksSql:
    def __init__(self, sessao: AsyncSession) -> None:
        self._sessao = sessao

    async def registrar(self, webhook: WebhookRecebido) -> bool:
        # A PK em event_id deduplica: a entrega concorrente do mesmo evento espera o commit desta
        # transação e então cai no ON CONFLICT.
        registrado = await self._sessao.scalar(
            insert(WebhookRecebidoModel)
            .values(
                event_id=webhook.event_id,
                transacao_externa_id=webhook.transacao_externa_id,
                tipo=webhook.tipo,
                payload_hash=webhook.hash_do_corpo,
                recebido_em=webhook.recebido_em,
            )
            .on_conflict_do_nothing(index_elements=[WebhookRecebidoModel.event_id])
            .returning(WebhookRecebidoModel.event_id)
        )
        return registrado is not None


def _pagamento(modelo: PagamentoModel) -> Pagamento:
    return Pagamento(
        id=modelo.id,
        pedido_id=modelo.pedido_id,
        status=StatusPagamento(modelo.status),
        forma=FormaPagamento(modelo.forma),
        valor=Dinheiro(modelo.valor),
        solicitado_em=modelo.solicitado_em,
        transacao_externa_id=modelo.transacao_externa_id,
        motivo_recusa=modelo.motivo_recusa,
        tentativas=modelo.tentativas,
        concluido_em=modelo.concluido_em,
    )
