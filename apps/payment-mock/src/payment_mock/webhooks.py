import asyncio
import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx

from payment_mock.assinatura import cabecalhos_do_webhook
from payment_mock.cenarios import StatusTransacao
from payment_mock.configuracao import Configuracao
from payment_mock.transacoes import Transacao

TIPO_DO_EVENTO = {
    StatusTransacao.APROVADO: "pagamento.aprovado",
    StatusTransacao.RECUSADO: "pagamento.recusado",
}

logger = logging.getLogger(__name__)


class EntregadorDeWebhooks:
    """Envia o resultado da transação por webhook assinado, depois de um atraso, como um provedor real.

    Entrega at-least-once: repete em resposta não-2xx, timeout ou erro de conexão. Por isso o receptor
    precisa deduplicar pelo `eventId`.
    """

    def __init__(self, cliente: httpx.AsyncClient, configuracao: Configuracao) -> None:
        self._cliente = cliente
        self._configuracao = configuracao
        self._pendentes: set[asyncio.Task[None]] = set()

    def agendar(self, transacao: Transacao) -> None:
        tarefa = asyncio.create_task(self._processar(transacao))
        # A referência evita que o coletor de lixo descarte a tarefa antes de ela terminar.
        self._pendentes.add(tarefa)
        tarefa.add_done_callback(self._ao_terminar)

    async def aguardar_entregas(self) -> None:
        while self._pendentes:
            await asyncio.gather(*self._pendentes, return_exceptions=True)

    async def encerrar(self) -> None:
        for tarefa in self._pendentes:
            tarefa.cancel()
        await asyncio.gather(*self._pendentes, return_exceptions=True)

    async def _processar(self, transacao: Transacao) -> None:
        await asyncio.sleep(self._configuracao.atraso_webhook_ms / 1000)
        transacao.concluir()
        evento = _evento(transacao)
        corpo = json.dumps(evento, separators=(",", ":")).encode()
        envios = (
            self._entregar(evento["eventId"], corpo) for _ in range(transacao.cenario.envios_do_webhook)
        )
        await asyncio.gather(*envios)

    async def _entregar(self, event_id: str, corpo: bytes) -> None:
        for espera in (0, *self._configuracao.esperas_de_reenvio):
            await asyncio.sleep(espera)
            if await self._tentar(event_id, corpo):
                return
        logger.warning("webhook_nao_entregue event_id=%s", event_id)

    async def _tentar(self, event_id: str, corpo: bytes) -> bool:
        cabecalhos = cabecalhos_do_webhook(
            event_id=event_id,
            corpo=corpo,
            timestamp=int(datetime.now(UTC).timestamp()),
            segredo=self._configuracao.segredo_webhook,
        )
        try:
            resposta = await self._cliente.post(
                self._configuracao.url_webhook,
                content=corpo,
                headers=cabecalhos,
                timeout=self._configuracao.timeout_entrega_segundos,
            )
        except httpx.HTTPError as erro:
            logger.info("webhook_falhou event_id=%s erro=%s", event_id, type(erro).__name__)
            return False
        logger.info("webhook_enviado event_id=%s status=%s", event_id, resposta.status_code)
        return resposta.is_success

    def _ao_terminar(self, tarefa: asyncio.Task[None]) -> None:
        self._pendentes.discard(tarefa)
        if not tarefa.cancelled() and tarefa.exception() is not None:
            logger.error("entrega_de_webhook_abortada", exc_info=tarefa.exception())


def _evento(transacao: Transacao) -> dict[str, Any]:
    return {
        "eventId": str(uuid.uuid4()),
        "tipo": TIPO_DO_EVENTO[transacao.status],
        "transacaoId": transacao.transacao_id,
        "pagamentoId": str(transacao.pagamento_id),
        "pedidoId": str(transacao.pedido_id),
        "status": transacao.status.value,
        "valor": float(transacao.valor),
        "motivo": transacao.motivo,
        "ocorridoEm": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }
