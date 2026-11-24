from raizes_api.application.autorizacao import VerificacaoDeEscopo
from raizes_api.application.paginacao import Pagina, Paginacao
from raizes_api.application.ports.leitura import LeituraCatalogo, LeituraEstoque, SaldoEstoque
from raizes_api.application.queries.catalogo import unidade_ativa
from raizes_api.domain.compartilhado.atores import AtorAutenticado

ENTIDADE_ESTOQUE = "ESTOQUE"


class ConsultarEstoque:
    def __init__(
        self, catalogo: LeituraCatalogo, estoque: LeituraEstoque, escopo: VerificacaoDeEscopo
    ) -> None:
        self._catalogo = catalogo
        self._estoque = estoque
        self._escopo = escopo

    async def executar(
        self, ator: AtorAutenticado, unidade_id: int, paginacao: Paginacao
    ) -> Pagina[SaldoEstoque]:
        await self._escopo.exigir(ator, unidade_id, entidade=ENTIDADE_ESTOQUE, entidade_id=str(unidade_id))
        await unidade_ativa(self._catalogo, unidade_id)
        return await self._estoque.saldos(unidade_id, paginacao)
