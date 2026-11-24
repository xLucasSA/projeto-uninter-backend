from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from raizes_api.api.schemas.erros import DetalheErroResponse, ErroResponse
from raizes_api.application.correlacao import contexto_requisicao_atual
from raizes_api.domain.compartilhado.erros import DetalheErro, ErroDominio

logger = structlog.get_logger(__name__)

STATUS_POR_CODIGO: dict[str, int] = {
    "REQUISICAO_MALFORMADA": 400,
    "REQUISICAO_INVALIDA": 400,
    "IDEMPOTENCY_KEY_AUSENTE": 400,
    "TOKEN_AUSENTE": 401,
    "TOKEN_INVALIDO": 401,
    "CREDENCIAIS_INVALIDAS": 401,
    "REFRESH_TOKEN_INVALIDO": 401,
    "REFRESH_TOKEN_REUTILIZADO": 401,
    "ASSINATURA_WEBHOOK_INVALIDA": 401,
    "PERMISSAO_NEGADA": 403,
    "FORA_DO_ESCOPO_UNIDADE": 403,
    "CANAL_INCOMPATIVEL": 403,
    "UNIDADE_NAO_ENCONTRADA": 404,
    "PRODUTO_NAO_ENCONTRADO": 404,
    "PEDIDO_NAO_ENCONTRADO": 404,
    "CONSENTIMENTO_NAO_ENCONTRADO": 404,
    "RECURSO_NAO_ENCONTRADO": 404,
    "METODO_NAO_PERMITIDO": 405,
    "EMAIL_JA_CADASTRADO": 409,
    "TELEFONE_JA_CADASTRADO": 409,
    "CONSENTIMENTO_JA_ATIVO": 409,
    "PRODUTO_INDISPONIVEL_NA_UNIDADE": 409,
    "ESTOQUE_INSUFICIENTE": 409,
    "TRANSICAO_STATUS_INVALIDA": 409,
    "PAGAMENTO_NAO_PERMITIDO": 409,
    "PAGAMENTO_EM_ANDAMENTO": 409,
    "REQUISICAO_EM_PROCESSAMENTO": 409,
    "IDEMPOTENCY_KEY_REUTILIZADA": 422,
    "VALIDACAO": 422,
    "ERRO_INTERNO": 500,
    "GATEWAY_INDISPONIVEL": 503,
    "SERVICO_INDISPONIVEL": 503,
}

MENSAGEM_VALIDACAO = "Um ou mais campos são inválidos."
MENSAGEM_JSON_INVALIDO = "O corpo da requisição não é um JSON válido."
MENSAGEM_ERRO_INTERNO = "Ocorreu um erro inesperado. Tente novamente mais tarde."
MENSAGENS_HTTP: dict[int, tuple[str, str]] = {
    404: ("RECURSO_NAO_ENCONTRADO", "O recurso solicitado não existe."),
    405: ("METODO_NAO_PERMITIDO", "O método HTTP não é permitido nesta rota."),
}
ORIGENS_DE_PARAMETRO = frozenset({"body", "query", "path", "header", "cookie"})
HEADERS_POR_CODIGO: dict[str, dict[str, str]] = {
    "REQUISICAO_EM_PROCESSAMENTO": {"Retry-After": "1"},
}


def resposta_de_erro(
    *,
    status: int,
    codigo: str,
    mensagem: str,
    caminho: str,
    detalhes: Sequence[DetalheErro] = (),
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    contexto = contexto_requisicao_atual()
    corpo = ErroResponse(
        error=codigo,
        message=mensagem,
        details=[DetalheErroResponse(field=item.campo, issue=item.problema) for item in detalhes],
        timestamp=datetime.now(UTC).replace(microsecond=0),
        path=caminho,
        request_id=contexto.request_id if contexto else None,
    )
    return JSONResponse(status_code=status, content=corpo.model_dump(mode="json"), headers=headers)


def resposta_de_erro_interno(caminho: str) -> JSONResponse:
    return resposta_de_erro(
        status=500, codigo="ERRO_INTERNO", mensagem=MENSAGEM_ERRO_INTERNO, caminho=caminho
    )


def campo_do_erro_de_validacao(localizacao: Sequence[str | int]) -> str:
    """Converte o `loc` do Pydantic no caminho do campo.

    ("body", "itens", 0, "quantidade") → "itens[0].quantidade".
    """
    partes = list(localizacao)
    if partes and partes[0] in ORIGENS_DE_PARAMETRO:
        partes = partes[1:]
    caminho = ""
    for parte in partes:
        if isinstance(parte, int):
            caminho += f"[{parte}]"
        else:
            caminho += f".{parte}" if caminho else parte
    return caminho or "body"


def descrever_erro_de_validacao(erro: dict[str, Any]) -> str:
    contexto = erro.get("ctx") or {}
    tipo = erro.get("type", "")
    descricoes = {
        "missing": "Campo obrigatório.",
        "greater_than_equal": f"Deve ser maior ou igual a {contexto.get('ge')}.",
        "greater_than": f"Deve ser maior que {contexto.get('gt')}.",
        "less_than_equal": f"Deve ser menor ou igual a {contexto.get('le')}.",
        "less_than": f"Deve ser menor que {contexto.get('lt')}.",
        "int_parsing": "Deve ser um número inteiro.",
        "int_type": "Deve ser um número inteiro.",
        "string_type": "Deve ser um texto.",
        "string_too_short": f"Deve ter pelo menos {contexto.get('min_length')} caractere(s).",
        "string_too_long": f"Deve ter no máximo {contexto.get('max_length')} caractere(s).",
        "too_short": f"Deve ter pelo menos {contexto.get('min_length')} item(ns).",
        "too_long": f"Deve ter no máximo {contexto.get('max_length')} item(ns).",
        "enum": f"Valor inválido. Valores aceitos: {contexto.get('expected')}.",
        "literal_error": f"Valor inválido. Valores aceitos: {contexto.get('expected')}.",
        "uuid_parsing": "Deve ser um UUID válido.",
        "uuid_type": "Deve ser um UUID válido.",
        "value_error": str(contexto.get("error", erro.get("msg", "Valor inválido."))),
        "extra_forbidden": "Campo não permitido.",
    }
    return descricoes.get(tipo, str(erro.get("msg", "Valor inválido.")))


async def tratar_erro_dominio(request: Request, erro: Exception) -> JSONResponse:
    if not isinstance(erro, ErroDominio):
        raise erro
    status = STATUS_POR_CODIGO.get(erro.codigo)
    if status is None:
        logger.error("codigo_de_erro_sem_status_http", codigo=erro.codigo)
        return resposta_de_erro_interno(request.url.path)
    return resposta_de_erro(
        status=status,
        codigo=erro.codigo,
        mensagem=erro.mensagem,
        caminho=request.url.path,
        detalhes=erro.detalhes,
        headers=HEADERS_POR_CODIGO.get(erro.codigo),
    )


async def tratar_erro_de_validacao(request: Request, erro: Exception) -> JSONResponse:
    if not isinstance(erro, RequestValidationError):
        raise erro
    erros = list(erro.errors())
    if any(item.get("type") == "json_invalid" for item in erros):
        return resposta_de_erro(
            status=400,
            codigo="REQUISICAO_MALFORMADA",
            mensagem=MENSAGEM_JSON_INVALIDO,
            caminho=request.url.path,
        )
    detalhes = [
        DetalheErro(campo=campo_do_erro_de_validacao(item["loc"]), problema=descrever_erro_de_validacao(item))
        for item in erros
    ]
    return resposta_de_erro(
        status=422,
        codigo="VALIDACAO",
        mensagem=MENSAGEM_VALIDACAO,
        caminho=request.url.path,
        detalhes=detalhes,
    )


async def tratar_erro_http(request: Request, erro: Exception) -> JSONResponse:
    if not isinstance(erro, StarletteHTTPException):
        raise erro
    codigo, mensagem = MENSAGENS_HTTP.get(
        erro.status_code, ("REQUISICAO_INVALIDA", "A requisição é inválida.")
    )
    if erro.status_code >= 500:
        return resposta_de_erro_interno(request.url.path)
    return resposta_de_erro(
        status=erro.status_code,
        codigo=codigo,
        mensagem=mensagem,
        caminho=request.url.path,
        headers=dict(erro.headers) if erro.headers else None,
    )


def registrar_tratadores(app: FastAPI) -> None:
    app.add_exception_handler(ErroDominio, tratar_erro_dominio)
    app.add_exception_handler(RequestValidationError, tratar_erro_de_validacao)
    app.add_exception_handler(StarletteHTTPException, tratar_erro_http)
