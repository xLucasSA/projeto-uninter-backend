import re
import time
import uuid

import structlog
from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from raizes_api.api.errors import resposta_de_erro_interno
from raizes_api.application.correlacao import (
    ContextoRequisicao,
    definir_contexto_requisicao,
    restaurar_contexto_requisicao,
)

HEADER_REQUEST_ID = "X-Request-ID"
# Só aceita o id do cliente se for curto e sem caracteres especiais: ele vai para logs e auditoria.
FORMATO_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
ROTA_NAO_MAPEADA = "-"

logger = structlog.get_logger("raizes_api.acesso")


class RequestIdMiddleware:
    """Correlaciona a requisição (X-Request-ID), registra o log de acesso e captura erros não tratados.

    Fica por fora de todos os outros middlewares: assim até o 500 sai no erro padrão com o requestId.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = _request_id_da_requisicao(scope)
        cliente = scope.get("client")
        token = definir_contexto_requisicao(
            ContextoRequisicao(request_id=request_id, ip=cliente[0] if cliente else None)
        )
        inicio = time.perf_counter()
        status = 500
        resposta_iniciada = False

        async def enviar_com_request_id(mensagem: Message) -> None:
            nonlocal status, resposta_iniciada
            if mensagem["type"] == "http.response.start":
                status = mensagem["status"]
                resposta_iniciada = True
                MutableHeaders(scope=mensagem)[HEADER_REQUEST_ID] = request_id
            await send(mensagem)

        try:
            await self.app(scope, receive, enviar_com_request_id)
        except Exception:
            logger.exception("erro_nao_tratado")
            if resposta_iniciada:
                raise
            await resposta_de_erro_interno(scope["path"])(scope, receive, enviar_com_request_id)
        finally:
            logger.info(
                "requisicao",
                metodo=scope["method"],
                rota=_rota(scope),
                status=status,
                duracaoMs=round((time.perf_counter() - inicio) * 1000, 1),
            )
            restaurar_contexto_requisicao(token)


def _request_id_da_requisicao(scope: Scope) -> str:
    recebido = Headers(scope=scope).get(HEADER_REQUEST_ID, "")
    if FORMATO_REQUEST_ID.fullmatch(recebido):
        return recebido
    return str(uuid.uuid4())


def _rota(scope: Scope) -> str:
    rota = scope.get("route")
    caminho = getattr(rota, "path", None)
    return caminho if isinstance(caminho, str) else ROTA_NAO_MAPEADA
