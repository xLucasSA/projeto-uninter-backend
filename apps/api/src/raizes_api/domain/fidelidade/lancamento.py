import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import TypeGuard

from raizes_api.domain.clientes.cliente import Cliente, FinalidadeConsentimento
from raizes_api.domain.compartilhado.dinheiro import Dinheiro

PONTOS_POR_REAL = 1


class TipoLancamento(StrEnum):
    CREDITO = "CREDITO"
    ESTORNO = "ESTORNO"


@dataclass(frozen=True, slots=True)
class LancamentoFidelidade:
    """Append-only: no máximo um CREDITO e um ESTORNO por pedido; o ESTORNO é o negativo do CREDITO."""

    id: uuid.UUID
    cliente_id: uuid.UUID
    pedido_id: uuid.UUID
    tipo: TipoLancamento
    pontos: int
    criado_em: datetime

    def estornar(self, agora: datetime) -> "LancamentoFidelidade":
        if self.tipo is not TipoLancamento.CREDITO:
            raise ValueError("Só um crédito pode ser estornado.")
        return LancamentoFidelidade(
            id=uuid.uuid4(),
            cliente_id=self.cliente_id,
            pedido_id=self.pedido_id,
            tipo=TipoLancamento.ESTORNO,
            pontos=-self.pontos,
            criado_em=agora,
        )


def pontos_pelo_total(total: Dinheiro) -> int:
    """Um ponto por real inteiro: R$ 129,70 → 129 pontos."""
    return total.reais_inteiros() * PONTOS_POR_REAL


def elegivel_a_pontos(cliente: Cliente | None) -> TypeGuard[Cliente]:
    """Pedido identificado, cliente não anonimizado e consentimento FIDELIDADE ativo na aprovação."""
    return (
        cliente is not None
        and cliente.anonimizado_em is None
        and cliente.tem_consentimento_ativo(FinalidadeConsentimento.FIDELIDADE)
    )


def credito_pelo_pedido(
    cliente: Cliente | None, *, pedido_id: uuid.UUID, total: Dinheiro, agora: datetime
) -> LancamentoFidelidade | None:
    """None quando o pedido não gera pontos (inelegível ou total abaixo de R$ 1,00)."""
    pontos = pontos_pelo_total(total)
    if not elegivel_a_pontos(cliente) or pontos <= 0:
        return None
    return LancamentoFidelidade(
        id=uuid.uuid4(),
        cliente_id=cliente.id,
        pedido_id=pedido_id,
        tipo=TipoLancamento.CREDITO,
        pontos=pontos,
        criado_em=agora,
    )
