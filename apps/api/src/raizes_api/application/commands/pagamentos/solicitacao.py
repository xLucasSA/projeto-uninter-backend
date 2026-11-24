import uuid
from collections.abc import Callable
from dataclasses import dataclass

from raizes_api.application.autorizacao import VerificacaoDeEscopo
from raizes_api.application.commands.pedidos.efeitos import AGREGADO_PAGAMENTO, auditoria_do_pedido, evento
from raizes_api.application.erros import GatewayIndisponivel
from raizes_api.application.idempotencia import RespostaIdempotente, reservar_ou_reproduzir
from raizes_api.application.ports.auditoria import AcaoAuditoria
from raizes_api.application.ports.gateway_pagamento import (
    GatewayPagamento,
    SolicitacaoPagamento,
    TransacaoAceita,
)
from raizes_api.application.ports.idempotencia import ChaveIdempotente, RespostaGravada
from raizes_api.application.ports.relogio import Relogio
from raizes_api.application.ports.unit_of_work import UnitOfWork
from raizes_api.domain.compartilhado.atores import AtorAutenticado
from raizes_api.domain.pagamentos.erros import PagamentoNaoPermitido
from raizes_api.domain.pagamentos.pagamento import FormaPagamento, Pagamento
from raizes_api.domain.pedidos.erros import PedidoNaoEncontrado
from raizes_api.domain.pedidos.pedido import Autoria, Pedido

ROTA_SOLICITAR_PAGAMENTO = "POST /pedidos/{pedidoId}/pagamentos"

ApresentadorDePagamento = Callable[[Pagamento], RespostaGravada]


@dataclass(frozen=True, slots=True)
class DadosPagamento:
    forma: FormaPagamento
    token_pagamento: str


@dataclass(frozen=True, slots=True)
class _PagamentoRegistrado:
    pedido: Pedido
    pagamento: Pagamento


class SolicitarPagamento:
    """Duas transações com a chamada ao gateway no meio (guideline 08).

    1. Reserva a `Idempotency-Key` (fica PROCESSANDO), valida o pedido e grava o pagamento PENDENTE.
    2. Chama o gateway, com retentativas (é seguro repetir: a chave do gateway é o `pagamentoId`).
    3. Sucesso: grava a transação externa e conclui a chave com o 202. Falha: pagamento ERRO, chave liberada
       e 503; o pedido continua AGUARDANDO_PAGAMENTO e aceita outra tentativa.

    O resultado do pagamento chega depois, pelo webhook (`ProcessarWebhookPagamento`).
    """

    def __init__(
        self,
        uow: UnitOfWork,
        relogio: Relogio,
        escopo: VerificacaoDeEscopo,
        gateway: GatewayPagamento,
        apresentar: ApresentadorDePagamento,
    ) -> None:
        self._uow = uow
        self._relogio = relogio
        self._escopo = escopo
        self._gateway = gateway
        self._apresentar = apresentar

    async def executar(
        self, ator: AtorAutenticado, pedido_id: uuid.UUID, dados: DadosPagamento, chave: ChaveIdempotente
    ) -> RespostaIdempotente:
        registrado = await self._registrar_solicitacao(ator, pedido_id, dados, chave)
        if isinstance(registrado, RespostaIdempotente):
            return registrado
        try:
            aceite = await self._gateway.solicitar(
                SolicitacaoPagamento(
                    pagamento_id=registrado.pagamento.id,
                    pedido_id=registrado.pedido.id,
                    valor=registrado.pagamento.valor,
                    token_pagamento=dados.token_pagamento,
                )
            )
        except GatewayIndisponivel as falha:
            return await self._registrar_falha(ator, registrado, chave, falha)
        return await self._registrar_aceite(registrado, chave, aceite)

    async def _registrar_solicitacao(
        self, ator: AtorAutenticado, pedido_id: uuid.UUID, dados: DadosPagamento, chave: ChaveIdempotente
    ) -> _PagamentoRegistrado | RespostaIdempotente:
        agora = self._relogio.agora()
        async with self._uow as uow:
            reproduzida = await reservar_ou_reproduzir(
                uow.idempotencia, chave, agora, retomar_abandonada=True
            )
            if reproduzida is not None:
                return reproduzida
            pedido = await uow.pedidos.obter_para_atualizacao(pedido_id)
            if pedido is None:
                raise PedidoNaoEncontrado()
            await self._escopo.exigir_acesso_ao_pedido(ator, pedido.id, pedido.vinculos)
            if not pedido.aguarda_pagamento or await uow.pagamentos.ativo_do_pedido(pedido.id) is not None:
                raise PagamentoNaoPermitido()

            pagamento = Pagamento.solicitar(
                pedido_id=pedido.id, valor=pedido.total, forma=dados.forma, agora=agora
            )
            await uow.pagamentos.adicionar(pagamento)
            await uow.auditoria.registrar(
                auditoria_do_pedido(
                    pedido,
                    Autoria.de(ator),
                    AcaoAuditoria.PAGAMENTO_SOLICITADO,
                    {"pagamentoId": pagamento.id, "valor": pagamento.valor.valor, "forma": pagamento.forma},
                )
            )
            await uow.outbox.publicar(
                evento(
                    pedido,
                    "PagamentoSolicitado",
                    AGREGADO_PAGAMENTO,
                    str(pagamento.id),
                    {"pagamentoId": pagamento.id, "pedidoId": pedido.id, "valor": pagamento.valor.valor},
                )
            )
            await uow.commit()
        return _PagamentoRegistrado(pedido=pedido, pagamento=pagamento)

    async def _registrar_aceite(
        self, registrado: _PagamentoRegistrado, chave: ChaveIdempotente, aceite: TransacaoAceita
    ) -> RespostaIdempotente:
        async with self._uow as uow:
            pagamento = await self._pagamento_atual(uow, registrado)
            pagamento.registrar_aceite(aceite.transacao_id, aceite.tentativas)
            await uow.pagamentos.atualizar(pagamento)
            return await self._concluir(uow, pagamento, chave)

    async def _registrar_falha(
        self,
        ator: AtorAutenticado,
        registrado: _PagamentoRegistrado,
        chave: ChaveIdempotente,
        falha: GatewayIndisponivel,
    ) -> RespostaIdempotente:
        async with self._uow as uow:
            pagamento = await self._pagamento_atual(uow, registrado)
            if not pagamento.esta_pendente:
                # O gateway processou, apesar do timeout, e o webhook chegou primeiro: vale o resultado dele.
                return await self._concluir(uow, pagamento, chave)
            pagamento.registrar_falha(falha.tentativas, self._relogio.agora())
            await uow.pagamentos.atualizar(pagamento)
            await uow.auditoria.registrar(
                auditoria_do_pedido(
                    registrado.pedido,
                    Autoria.de(ator),
                    AcaoAuditoria.PAGAMENTO_FALHOU,
                    {"pagamentoId": pagamento.id, "tentativas": falha.tentativas},
                )
            )
            await uow.idempotencia.liberar(chave)
            await uow.commit()
        raise falha

    async def _pagamento_atual(self, uow: UnitOfWork, registrado: _PagamentoRegistrado) -> Pagamento:
        # O bloqueio do pedido serializa esta transação com o webhook, que pode ter chegado durante a chamada.
        await uow.pedidos.obter_para_atualizacao(registrado.pedido.id)
        pagamento = await uow.pagamentos.obter(registrado.pagamento.id)
        if pagamento is None:
            raise RuntimeError("O pagamento gravado na primeira transação sumiu.")
        return pagamento

    async def _concluir(
        self, uow: UnitOfWork, pagamento: Pagamento, chave: ChaveIdempotente
    ) -> RespostaIdempotente:
        resposta = self._apresentar(pagamento)
        await uow.idempotencia.concluir(chave, resposta)
        await uow.commit()
        return RespostaIdempotente(status_code=resposta.status_code, corpo=resposta.corpo, reproduzida=False)
