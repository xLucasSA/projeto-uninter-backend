from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from importlib.metadata import version

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from raizes_api.api.errors import registrar_tratadores
from raizes_api.api.middlewares import HEADER_REQUEST_ID, RequestIdMiddleware
from raizes_api.api.openapi import DESCRICAO_API, TAGS
from raizes_api.api.routers import (
    auditoria,
    autenticacao,
    clientes,
    fidelidade,
    health,
    pagamentos,
    pedidos,
    produtos,
    unidades,
    webhooks,
)
from raizes_api.application.commands.autenticacao.sessoes import ValidadesSessao
from raizes_api.application.ports.gateway_pagamento import GatewayPagamento
from raizes_api.infrastructure.db.banco import BancoDeDados
from raizes_api.infrastructure.gateway.pagamentos import GatewayPagamentoHttp
from raizes_api.infrastructure.leitura.banco_de_escrita import (
    LeituraAuditoriaSql,
    LeituraCatalogoSql,
    LeituraEstoqueSql,
    LeituraFidelidadeSql,
    LeituraPagamentosSql,
    LeituraPedidosSql,
)
from raizes_api.infrastructure.observabilidade.logs import configurar_logs
from raizes_api.infrastructure.relogio import RelogioSistema
from raizes_api.infrastructure.security.senhas import HasherSenhaArgon2
from raizes_api.infrastructure.security.tokens import EmissorTokensJwt
from raizes_api.infrastructure.security.webhooks import VerificadorAssinaturaHmac
from raizes_api.settings import Settings

HEADERS_EXPOSTOS = [HEADER_REQUEST_ID, "Location", "Idempotent-Replayed", "Retry-After"]


def create_app(settings: Settings | None = None, gateway: GatewayPagamento | None = None) -> FastAPI:
    """`gateway` substitui o cliente HTTP do payment-mock (testes usam um fake configurável)."""
    configuracao = settings or Settings()
    configurar_logs(configuracao.log_level)
    banco = BancoDeDados(configuracao.database_url)
    relogio = RelogioSistema()
    cliente_gateway: httpx.AsyncClient | None = None
    if gateway is None:
        cliente_gateway = httpx.AsyncClient(
            base_url=configuracao.payment_gateway_url,
            timeout=httpx.Timeout(configuracao.payment_gateway_timeout_seconds),
        )
        gateway = GatewayPagamentoHttp(
            cliente_gateway, max_retentativas=configuracao.payment_gateway_max_retries
        )

    @asynccontextmanager
    async def ciclo_de_vida(_app: FastAPI) -> AsyncIterator[None]:
        yield
        if cliente_gateway is not None:
            await cliente_gateway.aclose()
        await banco.encerrar()

    app = FastAPI(
        title="Raízes do Nordeste — API",
        version=version("raizes-api"),
        description=DESCRICAO_API,
        openapi_tags=TAGS,
        lifespan=ciclo_de_vida,
    )
    app.state.banco = banco
    app.state.relogio = relogio
    app.state.settings = configuracao
    app.state.hasher = HasherSenhaArgon2()
    app.state.emissor_tokens = EmissorTokensJwt(configuracao.jwt_secret, relogio)
    app.state.gateway_pagamento = gateway
    app.state.verificador_webhook = VerificadorAssinaturaHmac(configuracao.payment_webhook_secret, relogio)
    app.state.validades_sessao = ValidadesSessao(
        acesso=configuracao.validade_acesso(),
        refresh=configuracao.validade_refresh(),
        dispositivo=configuracao.validade_dispositivo(),
    )

    _configurar_leitura(app, configuracao, banco)

    registrar_tratadores(app)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=configuracao.origens_cors(),
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=HEADERS_EXPOSTOS,
    )
    app.add_middleware(RequestIdMiddleware)

    app.include_router(autenticacao.router)
    app.include_router(clientes.router)
    app.include_router(unidades.router)
    app.include_router(produtos.router)
    app.include_router(pedidos.router)
    app.include_router(pagamentos.router)
    app.include_router(webhooks.router)
    app.include_router(fidelidade.router)
    app.include_router(auditoria.router)
    app.include_router(health.router)
    return app


def _configurar_leitura(app: FastAPI, configuracao: Settings, banco: BancoDeDados) -> None:
    """Fonte das consultas (CQRS). `read` depende do read model alimentado por CDC, que é do T3."""
    if configuracao.read_model_source != "write":
        raise RuntimeError("READ_MODEL_SOURCE=read exige o read model (T3), que não faz parte desta entrega.")
    app.state.leitura_catalogo = LeituraCatalogoSql(banco.fabrica_sessoes)
    app.state.leitura_estoque = LeituraEstoqueSql(banco.fabrica_sessoes)
    app.state.leitura_pedidos = LeituraPedidosSql(banco.fabrica_sessoes)
    app.state.leitura_pagamentos = LeituraPagamentosSql(banco.fabrica_sessoes)
    app.state.leitura_fidelidade = LeituraFidelidadeSql(banco.fabrica_sessoes)
    app.state.leitura_auditoria = LeituraAuditoriaSql(banco.fabrica_sessoes)
