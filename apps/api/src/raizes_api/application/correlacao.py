from contextvars import ContextVar, Token
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ContextoRequisicao:
    request_id: str
    ip: str | None


_contexto_atual: ContextVar[ContextoRequisicao | None] = ContextVar("contexto_requisicao", default=None)


def definir_contexto_requisicao(contexto: ContextoRequisicao) -> Token[ContextoRequisicao | None]:
    return _contexto_atual.set(contexto)


def restaurar_contexto_requisicao(token: Token[ContextoRequisicao | None]) -> None:
    _contexto_atual.reset(token)


def contexto_requisicao_atual() -> ContextoRequisicao | None:
    return _contexto_atual.get()
