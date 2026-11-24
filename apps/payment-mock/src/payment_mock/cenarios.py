from dataclasses import dataclass
from enum import StrEnum


class StatusTransacao(StrEnum):
    PENDENTE = "PENDENTE"
    APROVADO = "APROVADO"
    RECUSADO = "RECUSADO"


@dataclass(frozen=True, slots=True)
class Cenario:
    """O que o gateway simulado faz com um `tokenPagamento` (tabela do guideline 08)."""

    resultado: StatusTransacao
    motivo: str | None = None
    responde_a_tempo: bool = True
    envios_do_webhook: int = 1

    @property
    def envia_webhook(self) -> bool:
        return self.responde_a_tempo and self.envios_do_webhook > 0


APROVADO = Cenario(resultado=StatusTransacao.APROVADO)
RECUSADO = Cenario(resultado=StatusTransacao.RECUSADO, motivo="SALDO_INSUFICIENTE")
SEM_RESPOSTA = Cenario(resultado=StatusTransacao.PENDENTE, responde_a_tempo=False, envios_do_webhook=0)
WEBHOOK_DUPLICADO = Cenario(resultado=StatusTransacao.APROVADO, envios_do_webhook=2)
TOKEN_INVALIDO = Cenario(resultado=StatusTransacao.RECUSADO, motivo="TOKEN_INVALIDO")

CENARIO_POR_TOKEN = {
    "tok_aprovado": APROVADO,
    "tok_recusado": RECUSADO,
    "tok_timeout": SEM_RESPOSTA,
    "tok_webhook_duplicado": WEBHOOK_DUPLICADO,
}


def cenario_do_token(token: str) -> Cenario:
    return CENARIO_POR_TOKEN.get(token, TOKEN_INVALIDO)
