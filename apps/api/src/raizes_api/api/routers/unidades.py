from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from raizes_api.api.dependencies.autenticacao import exigir_perfis
from raizes_api.api.dependencies.consultas import (
    obter_consultar_cardapio,
    obter_consultar_estoque,
    obter_listar_unidades,
    obter_obter_unidade,
    parametros_de_paginacao,
)
from raizes_api.api.openapi import respostas_de_erro
from raizes_api.api.schemas.catalogo import ItemCardapioResponse, SaldoEstoqueResponse, UnidadeResponse
from raizes_api.api.schemas.paginacao import PaginaResponse
from raizes_api.application.paginacao import Paginacao
from raizes_api.application.queries.catalogo import ConsultarCardapio, ListarUnidades, ObterUnidade
from raizes_api.application.queries.estoque import ConsultarEstoque
from raizes_api.domain.catalogo.catalogo import CategoriaProduto
from raizes_api.domain.compartilhado.atores import AtorAutenticado, Perfil

router = APIRouter(prefix="/unidades", tags=["Unidades"])
exigir_gestao_de_estoque = exigir_perfis(Perfil.ESTOQUISTA, Perfil.GERENTE, Perfil.MATRIZ)
IdDaUnidade = Annotated[int, Path(alias="unidadeId", ge=1, description="ID da unidade.")]


@router.get(
    "",
    summary="Listar unidades",
    description="Unidades ativas da rede, ordenadas pelo código.",
    responses=respostas_de_erro(422),
)
async def listar_unidades(
    paginacao: Paginacao = Depends(parametros_de_paginacao),
    consulta: ListarUnidades = Depends(obter_listar_unidades),
) -> PaginaResponse[UnidadeResponse]:
    pagina = await consulta.executar(paginacao)
    return PaginaResponse[UnidadeResponse].de(pagina, [UnidadeResponse.de(item) for item in pagina.itens])


@router.get(
    "/{unidadeId}",
    summary="Detalhar unidade",
    description="Unidade ativa. Inexistente ou inativa: 404 `UNIDADE_NAO_ENCONTRADA`.",
    responses=respostas_de_erro(404, 422),
)
async def obter_unidade(
    unidade_id: IdDaUnidade, consulta: ObterUnidade = Depends(obter_obter_unidade)
) -> UnidadeResponse:
    return UnidadeResponse.de(await consulta.executar(unidade_id))


@router.get(
    "/{unidadeId}/cardapio",
    summary="Cardápio da unidade",
    description=(
        "Produtos vendáveis hoje na unidade (data de São Paulo): item e produto ativos, dentro da janela "
        "sazonal, com o preço local. `disponivel` indica saldo em estoque; a criação do pedido revalida tudo."
    ),
    responses=respostas_de_erro(404, 422),
)
async def consultar_cardapio(
    unidade_id: IdDaUnidade,
    categoria: CategoriaProduto | None = Query(default=None, description="Filtra por categoria."),
    paginacao: Paginacao = Depends(parametros_de_paginacao),
    consulta: ConsultarCardapio = Depends(obter_consultar_cardapio),
) -> PaginaResponse[ItemCardapioResponse]:
    pagina = await consulta.executar(unidade_id, categoria, paginacao)
    return PaginaResponse[ItemCardapioResponse].de(
        pagina, [ItemCardapioResponse.de(item) for item in pagina.itens]
    )


@router.get(
    "/{unidadeId}/estoque",
    summary="Saldo de estoque da unidade",
    description=(
        "Saldo por produto. Perfis `ESTOQUISTA`, `GERENTE` (unidades do escopo) e `MATRIZ` (todas). "
        "Unidade fora do escopo: 403 `FORA_DO_ESCOPO_UNIDADE`, registrado na auditoria."
    ),
    responses=respostas_de_erro(401, 403, 404, 422),
)
async def consultar_estoque(
    unidade_id: IdDaUnidade,
    paginacao: Paginacao = Depends(parametros_de_paginacao),
    ator: AtorAutenticado = Depends(exigir_gestao_de_estoque),
    consulta: ConsultarEstoque = Depends(obter_consultar_estoque),
) -> PaginaResponse[SaldoEstoqueResponse]:
    pagina = await consulta.executar(ator, unidade_id, paginacao)
    return PaginaResponse[SaldoEstoqueResponse].de(
        pagina, [SaldoEstoqueResponse.de(item) for item in pagina.itens]
    )
