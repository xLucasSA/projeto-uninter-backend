import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from raizes_api.domain.compartilhado.atores import AtorAutenticado, TipoAtor
from raizes_api.domain.compartilhado.dinheiro import Dinheiro

# Ator das transições disparadas pelo webhook do gateway (guideline 03).
GATEWAY_DE_PAGAMENTO = AtorAutenticado(tipo=TipoAtor.SISTEMA, id="GATEWAY_PAGAMENTO", perfis=frozenset())


class StatusPagamento(StrEnum):
    PENDENTE = "PENDENTE"
    APROVADO = "APROVADO"
    RECUSADO = "RECUSADO"
    ERRO = "ERRO"


class FormaPagamento(StrEnum):
    MOCK = "MOCK"


class ResultadoDoGateway(StrEnum):
    APROVADO = "APROVADO"
    RECUSADO = "RECUSADO"


STATUS_ATIVOS = frozenset({StatusPagamento.PENDENTE, StatusPagamento.APROVADO})


@dataclass(eq=False, slots=True)
class Pagamento:
    """No máximo um pagamento ativo (PENDENTE ou APROVADO) por pedido; o valor é o total do pedido.

    `ERRO` é final: o gateway não confirmou o recebimento e o pedido aceita uma nova tentativa. Um webhook
    tardio para esse pagamento é ignorado e fica para a reconciliação (documentada).
    """

    id: uuid.UUID
    pedido_id: uuid.UUID
    status: StatusPagamento
    forma: FormaPagamento
    valor: Dinheiro
    solicitado_em: datetime
    transacao_externa_id: str | None = None
    motivo_recusa: str | None = None
    tentativas: int = 0
    concluido_em: datetime | None = None

    @classmethod
    def solicitar(
        cls, *, pedido_id: uuid.UUID, valor: Dinheiro, forma: FormaPagamento, agora: datetime
    ) -> "Pagamento":
        return cls(
            id=uuid.uuid4(),
            pedido_id=pedido_id,
            status=StatusPagamento.PENDENTE,
            forma=forma,
            valor=valor,
            solicitado_em=agora,
        )

    @property
    def esta_ativo(self) -> bool:
        return self.status in STATUS_ATIVOS

    @property
    def esta_pendente(self) -> bool:
        return self.status is StatusPagamento.PENDENTE

    def registrar_aceite(self, transacao_externa_id: str, tentativas: int) -> None:
        self.transacao_externa_id = transacao_externa_id
        self.tentativas = tentativas

    def registrar_falha(self, tentativas: int, agora: datetime) -> None:
        self._concluir(StatusPagamento.ERRO, agora)
        self.tentativas = tentativas

    def aplicar_resultado(
        self, resultado: ResultadoDoGateway, *, transacao_externa_id: str, motivo: str | None, agora: datetime
    ) -> None:
        if self.transacao_externa_id is None:
            # O webhook pode chegar antes de a API gravar a resposta do gateway.
            self.transacao_externa_id = transacao_externa_id
        if resultado is ResultadoDoGateway.APROVADO:
            self._concluir(StatusPagamento.APROVADO, agora)
        else:
            self._concluir(StatusPagamento.RECUSADO, agora)
            self.motivo_recusa = motivo

    def _concluir(self, status: StatusPagamento, agora: datetime) -> None:
        if not self.esta_pendente:
            raise ValueError(f"Pagamento {self.status} não pode mudar para {status}.")
        self.status = status
        self.concluido_em = agora
