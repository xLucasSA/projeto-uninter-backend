import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from payment_mock.cenarios import Cenario, StatusTransacao


@dataclass(slots=True)
class Transacao:
    transacao_id: str
    pagamento_id: uuid.UUID
    pedido_id: uuid.UUID
    valor: Decimal
    moeda: str
    cenario: Cenario
    criada_em: datetime
    status: StatusTransacao = StatusTransacao.PENDENTE
    motivo: str | None = None

    @classmethod
    def nova(
        cls,
        *,
        pagamento_id: uuid.UUID,
        pedido_id: uuid.UUID,
        valor: Decimal,
        moeda: str,
        cenario: Cenario,
        agora: datetime,
    ) -> "Transacao":
        return cls(
            transacao_id=f"trx_{uuid.uuid4().hex}",
            pagamento_id=pagamento_id,
            pedido_id=pedido_id,
            valor=valor,
            moeda=moeda,
            cenario=cenario,
            criada_em=agora,
        )

    def mesma_solicitacao(self, pagamento_id: uuid.UUID, valor: Decimal) -> bool:
        return self.pagamento_id == pagamento_id and self.valor == valor

    def concluir(self) -> None:
        self.status = self.cenario.resultado
        self.motivo = self.cenario.motivo


class RegistroDeTransacoes:
    """Estado em memória: o mock não persiste nada e recomeça vazio a cada reinício."""

    def __init__(self) -> None:
        self._por_chave: dict[str, Transacao] = {}
        self._por_id: dict[str, Transacao] = {}

    def obter(self, transacao_id: str) -> Transacao | None:
        return self._por_id.get(transacao_id)

    def registrar_ou_obter(self, chave: str, criar: Callable[[], Transacao]) -> tuple[Transacao, bool]:
        """Retorna a transação da `Idempotency-Key` e se ela acabou de ser criada.

        Não há `await` entre a busca e a gravação: no event loop, a operação é atômica sem lock.
        """
        existente = self._por_chave.get(chave)
        if existente is not None:
            return existente, False
        transacao = criar()
        self._por_chave[chave] = transacao
        self._por_id[transacao.transacao_id] = transacao
        return transacao, True
