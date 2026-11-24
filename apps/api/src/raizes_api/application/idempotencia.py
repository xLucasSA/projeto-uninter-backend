import hashlib
import json
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from raizes_api.application.erros import IdempotencyKeyReutilizada, RequisicaoEmProcessamento
from raizes_api.application.ports.idempotencia import ChaveIdempotente, RepositorioIdempotencia
from raizes_api.domain.compartilhado.atores import AtorAutenticado

VALIDADE_DA_CHAVE = timedelta(hours=24)
# Só vale para comandos em duas transações (pagamento): a chave fica PROCESSANDO visível entre elas.
ABANDONO_DA_CHAVE_PROCESSANDO = timedelta(seconds=60)


@dataclass(frozen=True, slots=True)
class RespostaIdempotente:
    status_code: int
    corpo: dict[str, Any]
    reproduzida: bool


def chave_idempotente(
    ator: AtorAutenticado, *, rota: str, chave: uuid.UUID, corpo: Mapping[str, Any]
) -> ChaveIdempotente:
    """A chave vale por (sujeito do token, rota, chave): dois clientes podem usar o mesmo UUID sem colidir."""
    return ChaveIdempotente(
        sujeito=f"{ator.tipo.value}:{ator.id}",
        rota=rota,
        chave=chave,
        hash_requisicao=hash_do_corpo(corpo),
    )


def hash_do_corpo(corpo: Mapping[str, Any]) -> str:
    # JSON canônico (chaves ordenadas, sem espaços): a mesma requisição gera o mesmo hash
    # em qualquer ordem de campos.
    canonico = json.dumps(corpo, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonico.encode()).hexdigest()


async def reservar_ou_reproduzir(
    repositorio: RepositorioIdempotencia,
    chave: ChaveIdempotente,
    agora: datetime,
    *,
    retomar_abandonada: bool = False,
) -> RespostaIdempotente | None:
    """None: a chave é nova e ficou reservada nesta transação. Senão, a resposta gravada para reproduzir."""
    existente = await repositorio.reservar(
        chave,
        agora=agora,
        expira_em=agora + VALIDADE_DA_CHAVE,
        processando_abandonada_antes_de=agora - ABANDONO_DA_CHAVE_PROCESSANDO if retomar_abandonada else None,
    )
    if existente is None:
        return None
    if existente.hash_requisicao != chave.hash_requisicao:
        raise IdempotencyKeyReutilizada()
    if existente.resposta is None:
        raise RequisicaoEmProcessamento()
    return RespostaIdempotente(
        status_code=existente.resposta.status_code, corpo=existente.resposta.corpo, reproduzida=True
    )
