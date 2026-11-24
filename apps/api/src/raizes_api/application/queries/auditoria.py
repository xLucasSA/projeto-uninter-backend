from dataclasses import dataclass
from datetime import datetime

from raizes_api.application.autorizacao import VerificacaoDeEscopo
from raizes_api.application.paginacao import Pagina, Paginacao
from raizes_api.application.ports.leitura import FiltroAuditoria, LeituraAuditoria, RegistroDaTrilha
from raizes_api.application.queries.pedidos import PeriodoInvalido
from raizes_api.domain.compartilhado.atores import AtorAutenticado
from raizes_api.domain.compartilhado.erros import DetalheErro
from raizes_api.domain.compartilhado.escopo import unidades_do_escopo

ENTIDADE_UNIDADE = "UNIDADE"


@dataclass(frozen=True, slots=True)
class CriteriosDaTrilha:
    entidade: str | None = None
    entidade_id: str | None = None
    acao: str | None = None
    unidade_id: int | None = None
    inicio: datetime | None = None
    fim: datetime | None = None


class ConsultarAuditoria:
    """Trilha da API (`vendas.auditoria`). GERENTE vê as unidades do escopo; MATRIZ, a rede toda.

    Registros sem unidade (cadastro de cliente, login falho) só aparecem para a MATRIZ.
    """

    def __init__(self, leitura: LeituraAuditoria, escopo: VerificacaoDeEscopo) -> None:
        self._leitura = leitura
        self._escopo = escopo

    async def executar(
        self, ator: AtorAutenticado, criterios: CriteriosDaTrilha, paginacao: Paginacao
    ) -> Pagina[RegistroDaTrilha]:
        if criterios.inicio and criterios.fim and criterios.inicio > criterios.fim:
            raise PeriodoInvalido(
                detalhes=[DetalheErro("dataInicio", "Deve ser anterior ou igual a dataFim.")]
            )
        if criterios.unidade_id is not None:
            await self._escopo.exigir(
                ator, criterios.unidade_id, entidade=ENTIDADE_UNIDADE, entidade_id=str(criterios.unidade_id)
            )
        filtro = FiltroAuditoria(
            unidades=unidades_do_escopo(ator),
            entidade=criterios.entidade,
            entidade_id=criterios.entidade_id,
            acao=criterios.acao,
            unidade_id=criterios.unidade_id,
            inicio=criterios.inicio,
            fim=criterios.fim,
        )
        return await self._leitura.listar(filtro, paginacao)
