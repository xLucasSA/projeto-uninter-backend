from dataclasses import dataclass
from decimal import Decimal

from raizes_api.application.paginacao import Pagina, Paginacao
from raizes_api.application.ports.leitura import LeituraCatalogo, ProdutoResumo, UnidadeResumo
from raizes_api.application.ports.relogio import Relogio
from raizes_api.domain.catalogo.catalogo import CategoriaProduto
from raizes_api.domain.catalogo.erros import ProdutoNaoEncontrado, UnidadeNaoEncontrada
from raizes_api.domain.compartilhado.tempo import data_local


@dataclass(frozen=True, slots=True)
class ItemCardapio:
    """`disponivel`: vendável hoje e com saldo. O pedido revalida e responde 409 se o item acabou."""

    produto_id: int
    nome: str
    descricao: str
    categoria: CategoriaProduto
    preco: Decimal
    disponivel: bool


class ListarUnidades:
    def __init__(self, leitura: LeituraCatalogo) -> None:
        self._leitura = leitura

    async def executar(self, paginacao: Paginacao) -> Pagina[UnidadeResumo]:
        return await self._leitura.listar_unidades(paginacao)


class ObterUnidade:
    def __init__(self, leitura: LeituraCatalogo) -> None:
        self._leitura = leitura

    async def executar(self, unidade_id: int) -> UnidadeResumo:
        return await unidade_ativa(self._leitura, unidade_id)


class ConsultarCardapio:
    """Cardápio da unidade no dia (data de São Paulo): itens ativos, dentro da janela sazonal."""

    def __init__(self, leitura: LeituraCatalogo, relogio: Relogio) -> None:
        self._leitura = leitura
        self._relogio = relogio

    async def executar(
        self, unidade_id: int, categoria: CategoriaProduto | None, paginacao: Paginacao
    ) -> Pagina[ItemCardapio]:
        await unidade_ativa(self._leitura, unidade_id)
        hoje = data_local(self._relogio.agora())
        itens = []
        for item in await self._leitura.ofertas_da_unidade(unidade_id, categoria):
            preco = item.oferta.preco_em(hoje)
            if preco is None:
                continue
            itens.append(
                ItemCardapio(
                    produto_id=item.oferta.produto_id,
                    nome=item.oferta.nome_produto,
                    descricao=item.descricao,
                    categoria=item.categoria,
                    preco=preco.valor,
                    disponivel=item.quantidade_em_estoque > 0,
                )
            )
        return paginacao.recortar(itens)


class ListarProdutos:
    def __init__(self, leitura: LeituraCatalogo) -> None:
        self._leitura = leitura

    async def executar(
        self, categoria: CategoriaProduto | None, paginacao: Paginacao
    ) -> Pagina[ProdutoResumo]:
        return await self._leitura.listar_produtos(categoria, paginacao)


class ObterProduto:
    def __init__(self, leitura: LeituraCatalogo) -> None:
        self._leitura = leitura

    async def executar(self, produto_id: int) -> ProdutoResumo:
        produto = await self._leitura.obter_produto(produto_id)
        if produto is None:
            raise ProdutoNaoEncontrado("O produto não existe ou está inativo.")
        return produto


async def unidade_ativa(leitura: LeituraCatalogo, unidade_id: int) -> UnidadeResumo:
    unidade = await leitura.obter_unidade(unidade_id)
    if unidade is None:
        raise UnidadeNaoEncontrada()
    return unidade
