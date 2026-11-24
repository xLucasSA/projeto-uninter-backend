import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class ChaveIdempotente:
    sujeito: str
    rota: str
    chave: uuid.UUID
    hash_requisicao: str


@dataclass(frozen=True, slots=True)
class RespostaGravada:
    status_code: int
    corpo: dict[str, Any]


@dataclass(frozen=True, slots=True)
class RegistroIdempotencia:
    """`resposta` fica None enquanto a requisição original ainda está em processamento."""

    hash_requisicao: str
    resposta: RespostaGravada | None


class RepositorioIdempotencia(Protocol):
    async def reservar(
        self,
        chave: ChaveIdempotente,
        *,
        agora: datetime,
        expira_em: datetime,
        processando_abandonada_antes_de: datetime | None = None,
    ) -> RegistroIdempotencia | None:
        """Reserva a chave na transação atual e retorna None; se ela já existe, retorna o registro.

        Uma requisição concorrente com a mesma chave espera o commit (ou rollback) da primeira.
        Chave vencida é descartada e tratada como nova; com `processando_abandonada_antes_de`, também a
        chave que ficou PROCESSANDO desde antes desse instante (a requisição original não terminou).
        """
        ...

    async def concluir(self, chave: ChaveIdempotente, resposta: RespostaGravada) -> None: ...

    async def liberar(self, chave: ChaveIdempotente) -> None:
        """Apaga a reserva: a mesma chave pode ser usada de novo (falha do gateway, guideline 03)."""
        ...
