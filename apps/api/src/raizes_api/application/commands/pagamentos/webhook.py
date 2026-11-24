import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from raizes_api.application.commands.pedidos.efeitos import (
    AGREGADO_FIDELIDADE,
    AGREGADO_PAGAMENTO,
    auditoria_do_pedido,
    dados_da_mudanca,
    devolver_estoque,
    evento,
    gravar_mudanca_de_status,
    itens_do_evento,
)
from raizes_api.application.ports.auditoria import AcaoAuditoria
from raizes_api.application.ports.pagamentos import WebhookRecebido
from raizes_api.application.ports.relogio import Relogio
from raizes_api.application.ports.unit_of_work import UnitOfWork
from raizes_api.domain.fidelidade.lancamento import credito_pelo_pedido
from raizes_api.domain.pagamentos.pagamento import GATEWAY_DE_PAGAMENTO, Pagamento, ResultadoDoGateway
from raizes_api.domain.pedidos.pedido import MudancaDeStatusPedido, Pedido
from raizes_api.domain.pedidos.status import StatusPedido


@dataclass(frozen=True, slots=True)
class NotificacaoDePagamento:
    """Corpo do webhook, já com a assinatura conferida. `hash_do_corpo` é o SHA-256 do corpo bruto."""

    event_id: uuid.UUID
    tipo: str
    transacao_id: str
    pagamento_id: uuid.UUID
    pedido_id: uuid.UUID
    resultado: ResultadoDoGateway
    valor: Decimal
    motivo: str | None
    hash_do_corpo: str


class DesfechoDoWebhook(StrEnum):
    PROCESSADO = "PROCESSADO"
    DUPLICADO = "DUPLICADO"
    PAGAMENTO_JA_FINAL = "PAGAMENTO_JA_FINAL"
    PAGAMENTO_DESCONHECIDO = "PAGAMENTO_DESCONHECIDO"
    VALOR_DIVERGENTE = "VALOR_DIVERGENTE"

    @property
    def aplicado(self) -> bool:
        return self is DesfechoDoWebhook.PROCESSADO

    @property
    def exige_alerta(self) -> bool:
        """Assinado pelo gateway, mas sem correspondência aqui: alguém precisa olhar (log de alerta)."""
        return self in {DesfechoDoWebhook.PAGAMENTO_DESCONHECIDO, DesfechoDoWebhook.VALOR_DIVERGENTE}


class ProcessarWebhookPagamento:
    """Aplica o resultado do gateway ao pagamento e ao pedido, uma única vez por evento (guideline 08).

    Tudo que não é aplicado responde 200 mesmo assim: um 4xx faria o gateway repetir sem chance de sucesso.
    """

    def __init__(self, uow: UnitOfWork, relogio: Relogio) -> None:
        self._uow = uow
        self._relogio = relogio

    async def executar(self, notificacao: NotificacaoDePagamento) -> DesfechoDoWebhook:
        agora = self._relogio.agora()
        async with self._uow as uow:
            # O INSERT da deduplicação vem primeiro: a entrega repetida e concorrente espera este commit.
            primeira_entrega = await uow.webhooks.registrar(
                WebhookRecebido(
                    event_id=notificacao.event_id,
                    transacao_externa_id=notificacao.transacao_id,
                    tipo=notificacao.tipo,
                    hash_do_corpo=notificacao.hash_do_corpo,
                    recebido_em=agora,
                )
            )
            if not primeira_entrega:
                return DesfechoDoWebhook.DUPLICADO
            desfecho = await self._aplicar(uow, notificacao, agora)
            await uow.commit()
        return desfecho

    async def _aplicar(
        self, uow: UnitOfWork, notificacao: NotificacaoDePagamento, agora: datetime
    ) -> DesfechoDoWebhook:
        conhecido = await uow.pagamentos.obter(notificacao.pagamento_id)
        if conhecido is None or conhecido.pedido_id != notificacao.pedido_id:
            return DesfechoDoWebhook.PAGAMENTO_DESCONHECIDO
        # Bloqueia o pedido e só então relê o pagamento: APROVADO e RECUSADO concorrentes não se sobrepõem.
        pedido = await uow.pedidos.obter_para_atualizacao(conhecido.pedido_id)
        pagamento = await uow.pagamentos.obter(notificacao.pagamento_id)
        if pedido is None or pagamento is None:
            return DesfechoDoWebhook.PAGAMENTO_DESCONHECIDO
        if not pagamento.esta_pendente:
            return DesfechoDoWebhook.PAGAMENTO_JA_FINAL
        if pagamento.valor.valor != notificacao.valor:
            return DesfechoDoWebhook.VALOR_DIVERGENTE

        pagamento.aplicar_resultado(
            notificacao.resultado,
            transacao_externa_id=notificacao.transacao_id,
            motivo=notificacao.motivo,
            agora=agora,
        )
        await uow.pagamentos.atualizar(pagamento)
        if notificacao.resultado is ResultadoDoGateway.APROVADO:
            await _confirmar(uow, pedido, pagamento, agora)
        else:
            await _recusar(uow, pedido, pagamento, agora)
        return DesfechoDoWebhook.PROCESSADO


async def _confirmar(uow: UnitOfWork, pedido: Pedido, pagamento: Pagamento, agora: datetime) -> None:
    mudanca = pedido.mudar_status(StatusPedido.PAGO, GATEWAY_DE_PAGAMENTO, agora=agora)
    await gravar_mudanca_de_status(uow, pedido, mudanca)
    await uow.auditoria.registrar(
        auditoria_do_pedido(
            pedido,
            mudanca.autoria,
            AcaoAuditoria.PAGAMENTO_APROVADO,
            {"pagamentoId": pagamento.id, "valor": pagamento.valor.valor, **dados_da_mudanca(mudanca)},
        )
    )
    await uow.outbox.publicar(
        evento(
            pedido,
            "PagamentoAprovado",
            AGREGADO_PAGAMENTO,
            str(pagamento.id),
            {
                "pagamentoId": pagamento.id,
                "pedidoId": pedido.id,
                "canalPedido": pedido.canal,
                "valor": pagamento.valor.valor,
                "itens": itens_do_evento(pedido),
                "aprovadoEm": agora,
            },
        )
    )
    await _creditar_pontos(uow, pedido, mudanca, agora)


async def _creditar_pontos(
    uow: UnitOfWork, pedido: Pedido, mudanca: MudancaDeStatusPedido, agora: datetime
) -> None:
    """Elegibilidade lida na mesma transação da aprovação: vale o consentimento deste instante."""
    cliente = await uow.clientes.obter(pedido.cliente_id) if pedido.cliente_id else None
    credito = credito_pelo_pedido(cliente, pedido_id=pedido.id, total=pedido.total, agora=agora)
    if credito is None:
        return
    await uow.fidelidade.adicionar(credito)
    await uow.auditoria.registrar(
        auditoria_do_pedido(
            pedido, mudanca.autoria, AcaoAuditoria.PONTOS_CREDITADOS, {"pontos": credito.pontos}
        )
    )
    await uow.outbox.publicar(
        evento(
            pedido,
            "PontosCreditados",
            AGREGADO_FIDELIDADE,
            str(credito.cliente_id),
            {"clienteId": credito.cliente_id, "pedidoId": pedido.id, "pontos": credito.pontos},
        )
    )


async def _recusar(uow: UnitOfWork, pedido: Pedido, pagamento: Pagamento, agora: datetime) -> None:
    mudanca = pedido.mudar_status(
        StatusPedido.PAGAMENTO_RECUSADO, GATEWAY_DE_PAGAMENTO, agora=agora, motivo=pagamento.motivo_recusa
    )
    await gravar_mudanca_de_status(uow, pedido, mudanca)
    await devolver_estoque(uow, pedido, agora)
    await uow.auditoria.registrar(
        auditoria_do_pedido(
            pedido,
            mudanca.autoria,
            AcaoAuditoria.PAGAMENTO_RECUSADO,
            {"pagamentoId": pagamento.id, **dados_da_mudanca(mudanca)},
        )
    )
    await uow.outbox.publicar(
        evento(
            pedido,
            "PagamentoRecusado",
            AGREGADO_PAGAMENTO,
            str(pagamento.id),
            {"pagamentoId": pagamento.id, "pedidoId": pedido.id, "motivo": pagamento.motivo_recusa},
        )
    )
