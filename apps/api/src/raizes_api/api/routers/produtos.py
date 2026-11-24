from fastapi import APIRouter, Depends, Path, Query

from raizes_api.api.dependencies.consultas import (
    obter_listar_produtos,
    obter_obter_produto,
    parametros_de_paginacao,
)
from raizes_api.api.openapi import respostas_de_erro
from raizes_api.api.schemas.catalogo import ProdutoResponse
from raizes_api.api.schemas.paginacao import PaginaResponse
from raizes_api.application.paginacao import Paginacao
from raizes_api.application.queries.catalogo import ListarProdutos, ObterProduto
from raizes_api.domain.catalogo.catalogo import CategoriaProduto

router = APIRouter(prefix="/produtos", tags=["Produtos"])


@router.get(
    "",
    summary="Listar produtos",
    description="Produtos ativos da rede. Preço e disponibilidade dependem da unidade: veja o cardápio dela.",
    responses=respostas_de_erro(422),
)
async def listar_produtos(
    categoria: CategoriaProduto | None = Query(default=None, description="Filtra por categoria."),
    paginacao: Paginacao = Depends(parametros_de_paginacao),
    consulta: ListarProdutos = Depends(obter_listar_produtos),
) -> PaginaResponse[ProdutoResponse]:
    pagina = await consulta.executar(categoria, paginacao)
    return PaginaResponse[ProdutoResponse].de(pagina, [ProdutoResponse.de(item) for item in pagina.itens])


@router.get(
    "/{produtoId}",
    summary="Detalhar produto",
    description="Produto ativo. Inexistente ou inativo: 404 `PRODUTO_NAO_ENCONTRADO`.",
    responses=respostas_de_erro(404, 422),
)
async def obter_produto(
    produto_id: int = Path(alias="produtoId", ge=1, description="ID do produto."),
    consulta: ObterProduto = Depends(obter_obter_produto),
) -> ProdutoResponse:
    return ProdutoResponse.de(await consulta.executar(produto_id))
