"""Cliente HTTP do gateway de pagamento (o `payment-mock`, contrato no guideline 08)."""

from typing import Any

import httpx
import structlog
from tenacity import AsyncRetrying, retry_if_exception, stop_after_attempt, wait_exponential_jitter
from tenacity.wait import wait_base

from raizes_api.application.erros import GatewayIndisponivel
from raizes_api.application.ports.gateway_pagamento import SolicitacaoPagamento, TransacaoAceita

logger = structlog.get_logger(__name__)

MOEDA = "BRL"
# 0,2 s, 0,4 s... até 1 s, mais até 0,2 s de jitter: clientes que falharam juntos não repetem juntos.
ESPERA_ENTRE_TENTATIVAS = wait_exponential_jitter(multiplier=0.2, max=1.0, jitter=0.2)


class GatewayPagamentoHttp:
    """Retentativa só para timeout, erro de conexão e 5xx, com backoff exponencial e jitter.

    Repetir é seguro porque a `Idempotency-Key` enviada é o `pagamentoId`: o gateway devolve a mesma
    transação. Um 4xx não se resolve repetindo; ele encerra as tentativas.
    """

    def __init__(
        self,
        cliente: httpx.AsyncClient,
        *,
        max_retentativas: int,
        espera: wait_base = ESPERA_ENTRE_TENTATIVAS,
    ) -> None:
        self._cliente = cliente
        self._max_retentativas = max_retentativas
        self._espera = espera

    async def solicitar(self, solicitacao: SolicitacaoPagamento) -> TransacaoAceita:
        tentativas = 0
        try:
            async for tentativa in AsyncRetrying(
                stop=stop_after_attempt(self._max_retentativas + 1),
                wait=self._espera,
                retry=retry_if_exception(_vale_repetir),
                reraise=True,
            ):
                with tentativa:
                    tentativas = tentativa.retry_state.attempt_number
                    resposta = await self._enviar(solicitacao)
            transacao_id = _transacao_aceita(resposta)
        except (httpx.HTTPError, ValueError) as erro:
            logger.warning("gateway_indisponivel", tentativas=tentativas, motivo=_motivo(erro))
            raise GatewayIndisponivel(tentativas) from erro
        return TransacaoAceita(transacao_id=transacao_id, tentativas=tentativas)

    async def _enviar(self, solicitacao: SolicitacaoPagamento) -> httpx.Response:
        resposta = await self._cliente.post(
            "/transacoes",
            headers={"Idempotency-Key": str(solicitacao.pagamento_id)},
            json={
                "pagamentoId": str(solicitacao.pagamento_id),
                "pedidoId": str(solicitacao.pedido_id),
                "valor": float(solicitacao.valor.valor),
                "moeda": MOEDA,
                "tokenPagamento": solicitacao.token_pagamento,
            },
        )
        resposta.raise_for_status()
        return resposta


def _vale_repetir(erro: BaseException) -> bool:
    if isinstance(erro, httpx.HTTPStatusError):
        return erro.response.is_server_error
    return isinstance(erro, httpx.TransportError)


def _transacao_aceita(resposta: httpx.Response) -> str:
    corpo: Any = resposta.json()
    transacao_id = corpo.get("transacaoId") if isinstance(corpo, dict) else None
    if not isinstance(transacao_id, str) or not transacao_id:
        raise ValueError("Resposta do gateway sem transacaoId.")
    return transacao_id


def _motivo(erro: Exception) -> str:
    if isinstance(erro, httpx.HTTPStatusError):
        return f"HTTP {erro.response.status_code}"
    return type(erro).__name__
