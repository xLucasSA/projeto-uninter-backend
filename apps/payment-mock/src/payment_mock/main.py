import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from importlib.metadata import version
from typing import Annotated

import httpx
from fastapi import FastAPI, Header, HTTPException, Path, status

from payment_mock.cenarios import cenario_do_token
from payment_mock.configuracao import Configuracao
from payment_mock.esquemas import SolicitacaoTransacao, TransacaoAceitaResponse, TransacaoResponse
from payment_mock.transacoes import RegistroDeTransacoes, Transacao
from payment_mock.webhooks import EntregadorDeWebhooks

DESCRICAO = """
Simula um provedor de pagamento externo. Aceita a transação (202) e responde depois, por webhook assinado
com HMAC-SHA256, para a URL configurada em `PAYMENT_WEBHOOK_URL`.

Cenários pelo `tokenPagamento`: `tok_aprovado`, `tok_recusado`, `tok_timeout` (não responde a tempo,
sem webhook), `tok_webhook_duplicado` (o mesmo evento chega duas vezes) e qualquer outro `tok_*`
(recusado, `TOKEN_INVALIDO`).
Estado em memória: reiniciar o container apaga as transações.
"""


def create_app(
    configuracao: Configuracao | None = None, cliente_webhook: httpx.AsyncClient | None = None
) -> FastAPI:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    config = configuracao or Configuracao()
    cliente = cliente_webhook or httpx.AsyncClient()
    registro = RegistroDeTransacoes()
    entregador = EntregadorDeWebhooks(cliente, config)

    @asynccontextmanager
    async def ciclo_de_vida(_app: FastAPI) -> AsyncIterator[None]:
        yield
        await entregador.encerrar()
        if cliente_webhook is None:
            await cliente.aclose()

    app = FastAPI(
        title="Raízes do Nordeste — Gateway de pagamento (mock)",
        version=version("payment-mock"),
        description=DESCRICAO,
        lifespan=ciclo_de_vida,
    )
    app.state.entregador = entregador

    @app.get("/health", tags=["Health"], summary="Processo no ar")
    async def verificar_vida() -> dict[str, str]:
        return {"status": "ok"}

    @app.post(
        "/transacoes",
        status_code=status.HTTP_202_ACCEPTED,
        tags=["Transações"],
        summary="Solicitar pagamento",
        description=(
            "Aceita a transação e agenda o webhook com o resultado. "
            "A mesma `Idempotency-Key` devolve a mesma "
            "transação, sem novo webhook: é seguro repetir após timeout."
        ),
    )
    async def criar_transacao(
        corpo: SolicitacaoTransacao,
        idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key", max_length=100)] = None,
    ) -> TransacaoAceitaResponse:
        if not idempotency_key:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail={"error": "IDEMPOTENCY_KEY_AUSENTE", "message": "Envie o header Idempotency-Key."},
            )
        cenario = cenario_do_token(corpo.token_pagamento)
        if not cenario.responde_a_tempo:
            await asyncio.sleep(config.segundos_sem_resposta)
        transacao, criada = registro.registrar_ou_obter(
            idempotency_key,
            lambda: Transacao.nova(
                pagamento_id=corpo.pagamento_id,
                pedido_id=corpo.pedido_id,
                valor=corpo.valor,
                moeda=corpo.moeda,
                cenario=cenario,
                agora=datetime.now(UTC),
            ),
        )
        if not transacao.mesma_solicitacao(corpo.pagamento_id, corpo.valor):
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "error": "IDEMPOTENCY_KEY_REUTILIZADA",
                    "message": "Esta Idempotency-Key já foi usada com outro pagamento ou valor.",
                },
            )
        if criada and cenario.envia_webhook:
            entregador.agendar(transacao)
        return TransacaoAceitaResponse(transacao_id=transacao.transacao_id, status=transacao.status)

    @app.get(
        "/transacoes/{transacaoId}",
        tags=["Transações"],
        summary="Consultar transação",
        description="Status atual da transação. Usado pela reconciliação de pendentes (documentada).",
    )
    async def obter_transacao(
        transacao_id: Annotated[str, Path(alias="transacaoId", max_length=64)],
    ) -> TransacaoResponse:
        transacao = registro.obter(transacao_id)
        if transacao is None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                detail={"error": "TRANSACAO_NAO_ENCONTRADA", "message": "A transação não existe."},
            )
        return TransacaoResponse.de(transacao)

    return app
