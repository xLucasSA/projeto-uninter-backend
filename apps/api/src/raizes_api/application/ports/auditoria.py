from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol

from raizes_api.domain.compartilhado.atores import TipoAtor


class AcaoAuditoria(StrEnum):
    CLIENTE_CADASTRADO = "CLIENTE_CADASTRADO"
    CLIENTE_ANONIMIZADO = "CLIENTE_ANONIMIZADO"
    CONSENTIMENTO_CONCEDIDO = "CONSENTIMENTO_CONCEDIDO"
    CONSENTIMENTO_REVOGADO = "CONSENTIMENTO_REVOGADO"
    PEDIDO_CRIADO = "PEDIDO_CRIADO"
    PEDIDO_STATUS_ALTERADO = "PEDIDO_STATUS_ALTERADO"
    PEDIDO_CANCELADO = "PEDIDO_CANCELADO"
    PAGAMENTO_SOLICITADO = "PAGAMENTO_SOLICITADO"
    PAGAMENTO_APROVADO = "PAGAMENTO_APROVADO"
    PAGAMENTO_RECUSADO = "PAGAMENTO_RECUSADO"
    PAGAMENTO_FALHOU = "PAGAMENTO_FALHOU"
    PONTOS_CREDITADOS = "PONTOS_CREDITADOS"
    PONTOS_ESTORNADOS = "PONTOS_ESTORNADOS"
    LOGIN_FALHOU = "LOGIN_FALHOU"
    REFRESH_REUTILIZADO = "REFRESH_REUTILIZADO"
    ACESSO_NEGADO_ESCOPO = "ACESSO_NEGADO_ESCOPO"


@dataclass(frozen=True, slots=True)
class RegistroAuditoria:
    """Ação sensível a registrar. `dados` guarda só campos não pessoais (guideline 09)."""

    ator_tipo: TipoAtor
    ator_id: str
    acao: AcaoAuditoria
    entidade: str
    entidade_id: str
    unidade_id: int | None = None
    dados: Mapping[str, object] = field(default_factory=dict)


class GravadorAuditoria(Protocol):
    """Grava na transação da Unit of Work: o registro só existe se o comando fizer commit."""

    async def registrar(self, registro: RegistroAuditoria) -> None: ...


class GravadorAuditoriaIndependente(Protocol):
    """Grava em transação própria, já confirmada ao retornar.

    Só para ações que falham e têm a transação desfeita (`LOGIN_FALHOU`, `ACESSO_NEGADO_ESCOPO`).
    """

    async def registrar(self, registro: RegistroAuditoria) -> None: ...
