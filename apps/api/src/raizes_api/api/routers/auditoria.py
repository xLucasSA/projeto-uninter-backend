from fastapi import APIRouter, Depends, Query
from pydantic import AwareDatetime

from raizes_api.api.dependencies.autenticacao import exigir_perfis
from raizes_api.api.dependencies.consultas import obter_consultar_auditoria, parametros_de_paginacao
from raizes_api.api.openapi import respostas_de_erro
from raizes_api.api.schemas.auditoria import RegistroAuditoriaResponse
from raizes_api.api.schemas.paginacao import PaginaResponse
from raizes_api.application.paginacao import Paginacao
from raizes_api.application.ports.auditoria import AcaoAuditoria
from raizes_api.application.queries.auditoria import ConsultarAuditoria, CriteriosDaTrilha
from raizes_api.domain.compartilhado.atores import AtorAutenticado, Perfil

router = APIRouter(prefix="/auditoria", tags=["Auditoria"])

exigir_gerencia = exigir_perfis(Perfil.GERENTE, Perfil.MATRIZ)


@router.get(
    "",
    summary="Consultar trilha de auditoria",
    description=(
        "Ações sensíveis registradas pela API (`vendas.auditoria`), mais recentes primeiro. `GERENTE` vê as "
        "unidades do escopo (`unidadeId` fora dele → 403); `MATRIZ`, a rede toda, inclusive registros sem "
        "unidade. A trilha de um pedido (criação, pagamento, pontos e status) usa `entidade=PEDIDO`. "
        "A auditoria do back-office fica no admin."
    ),
    responses=respostas_de_erro(401, 403, 422),
)
async def consultar_auditoria(
    entidade: str | None = Query(default=None, max_length=40, examples=["PEDIDO"]),
    entidade_id: str | None = Query(default=None, alias="entidadeId", max_length=64),
    acao: AcaoAuditoria | None = Query(default=None),
    unidade_id: int | None = Query(default=None, alias="unidadeId", ge=1),
    data_inicio: AwareDatetime | None = Query(
        default=None, alias="dataInicio", description="ISO 8601 com fuso."
    ),
    data_fim: AwareDatetime | None = Query(default=None, alias="dataFim", description="ISO 8601 com fuso."),
    paginacao: Paginacao = Depends(parametros_de_paginacao),
    ator: AtorAutenticado = Depends(exigir_gerencia),
    consulta: ConsultarAuditoria = Depends(obter_consultar_auditoria),
) -> PaginaResponse[RegistroAuditoriaResponse]:
    criterios = CriteriosDaTrilha(
        entidade=entidade,
        entidade_id=entidade_id,
        acao=acao.value if acao else None,
        unidade_id=unidade_id,
        inicio=data_inicio,
        fim=data_fim,
    )
    pagina = await consulta.executar(ator, criterios, paginacao)
    return PaginaResponse[RegistroAuditoriaResponse].de(
        pagina, [RegistroAuditoriaResponse.de(item) for item in pagina.itens]
    )
