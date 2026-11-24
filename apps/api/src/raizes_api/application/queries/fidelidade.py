import uuid

from raizes_api.application.paginacao import Pagina, Paginacao
from raizes_api.application.ports.leitura import LancamentoResumo, LeituraFidelidade
from raizes_api.domain.compartilhado.atores import AtorAutenticado


class ConsultarSaldoDePontos:
    """Saldo = soma dos lançamentos. Revogar o consentimento não apaga o saldo (guideline 03)."""

    def __init__(self, leitura: LeituraFidelidade) -> None:
        self._leitura = leitura

    async def executar(self, cliente: AtorAutenticado) -> int:
        return await self._leitura.saldo(uuid.UUID(cliente.id))


class ConsultarExtratoDePontos:
    def __init__(self, leitura: LeituraFidelidade) -> None:
        self._leitura = leitura

    async def executar(self, cliente: AtorAutenticado, paginacao: Paginacao) -> Pagina[LancamentoResumo]:
        return await self._leitura.extrato(uuid.UUID(cliente.id), paginacao)
