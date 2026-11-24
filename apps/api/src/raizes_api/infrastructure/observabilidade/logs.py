import logging
from typing import Any

import structlog
from structlog.typing import EventDict, Processor

from raizes_api.application.correlacao import contexto_requisicao_atual

CAMPOS_SECRETOS = frozenset(
    {
        "senha",
        "password",
        "token",
        "accesstoken",
        "access_token",
        "refreshtoken",
        "refresh_token",
        "authorization",
        "x-signature",
        "segredo",
        "clientsecret",
        "client_secret",
    }
)
CAMPOS_EMAIL = frozenset({"email"})
CAMPOS_TELEFONE = frozenset({"telefone"})
DIGITOS_VISIVEIS_INICIO_TELEFONE = 3
DIGITOS_VISIVEIS_FIM_TELEFONE = 2
OCULTO = "***"
LOGGERS_DO_UVICORN = ("uvicorn", "uvicorn.error", "uvicorn.access")


def mascarar_email(email: str) -> str:
    local, _, dominio = email.partition("@")
    if not local or not dominio:
        return OCULTO
    return f"{local[0]}{OCULTO}@{dominio}"


def mascarar_telefone(telefone: str) -> str:
    visiveis = DIGITOS_VISIVEIS_INICIO_TELEFONE + DIGITOS_VISIVEIS_FIM_TELEFONE
    if len(telefone) <= visiveis:
        return OCULTO
    ocultos = "*" * (len(telefone) - visiveis)
    return (
        f"{telefone[:DIGITOS_VISIVEIS_INICIO_TELEFONE]}{ocultos}{telefone[-DIGITOS_VISIVEIS_FIM_TELEFONE:]}"
    )


def mascarar_dados_pessoais(_logger: Any, _metodo: str, evento: EventDict) -> EventDict:
    """Processor do structlog: oculta segredos e mascara e-mail/telefone pelo nome do campo (guideline 09)."""
    for chave, valor in evento.items():
        nome = chave.lower()
        if nome in CAMPOS_SECRETOS:
            evento[chave] = OCULTO
        elif nome in CAMPOS_EMAIL and isinstance(valor, str):
            evento[chave] = mascarar_email(valor)
        elif nome in CAMPOS_TELEFONE and isinstance(valor, str):
            evento[chave] = mascarar_telefone(valor)
    return evento


def adicionar_request_id(_logger: Any, _metodo: str, evento: EventDict) -> EventDict:
    contexto = contexto_requisicao_atual()
    if contexto is not None:
        evento.setdefault("requestId", contexto.request_id)
    return evento


def configurar_logs(nivel: str) -> None:
    processadores: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        adicionar_request_id,
        mascarar_dados_pessoais,
    ]
    structlog.configure(
        processors=[*processadores, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    formatador = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=processadores,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(ensure_ascii=False),
        ],
    )
    saida = logging.StreamHandler()
    saida.setFormatter(formatador)

    raiz = logging.getLogger()
    raiz.handlers = [saida]
    raiz.setLevel(nivel.upper())
    for nome in LOGGERS_DO_UVICORN:
        logger_uvicorn = logging.getLogger(nome)
        logger_uvicorn.handlers = []
        logger_uvicorn.propagate = True
