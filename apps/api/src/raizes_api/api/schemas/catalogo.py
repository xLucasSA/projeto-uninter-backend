from datetime import datetime

from pydantic import Field

from raizes_api.api.schemas.base import SchemaBase
from raizes_api.api.schemas.tipos import DinheiroJson
from raizes_api.application.ports.leitura import ProdutoResumo, SaldoEstoque, UnidadeResumo
from raizes_api.application.queries.catalogo import ItemCardapio
from raizes_api.domain.catalogo.catalogo import CategoriaProduto


class UnidadeResponse(SchemaBase):
    id: int = Field(examples=[1])
    codigo: str = Field(examples=["REC-01"])
    nome: str = Field(examples=["Recife Boa Viagem"])
    cidade: str = Field(examples=["Recife"])
    uf: str = Field(examples=["PE"])
    regiao: str = Field(examples=["NE"])
    tipo: str = Field(description="`COMPLETA` ou `REDUZIDA` (cozinha).", examples=["COMPLETA"])

    @classmethod
    def de(cls, unidade: UnidadeResumo) -> "UnidadeResponse":
        return cls(
            id=unidade.id,
            codigo=unidade.codigo,
            nome=unidade.nome,
            cidade=unidade.cidade,
            uf=unidade.uf,
            regiao=unidade.regiao,
            tipo=unidade.tipo,
        )


class ProdutoResponse(SchemaBase):
    id: int = Field(examples=[10])
    sku: str = Field(examples=["TAP-QUEIJO"])
    nome: str = Field(examples=["Tapioca de queijo coalho"])
    descricao: str
    categoria: CategoriaProduto

    @classmethod
    def de(cls, produto: ProdutoResumo) -> "ProdutoResponse":
        return cls(
            id=produto.id,
            sku=produto.sku,
            nome=produto.nome,
            descricao=produto.descricao,
            categoria=produto.categoria,
        )


class ItemCardapioResponse(SchemaBase):
    produto_id: int = Field(examples=[10])
    nome: str = Field(examples=["Tapioca de queijo coalho"])
    descricao: str
    categoria: CategoriaProduto
    preco: DinheiroJson = Field(description="Preço nesta unidade.", examples=[14.90])
    disponivel: bool = Field(description="Há saldo em estoque agora. O pedido revalida na criação.")

    @classmethod
    def de(cls, item: ItemCardapio) -> "ItemCardapioResponse":
        return cls(
            produto_id=item.produto_id,
            nome=item.nome,
            descricao=item.descricao,
            categoria=item.categoria,
            preco=item.preco,
            disponivel=item.disponivel,
        )


class SaldoEstoqueResponse(SchemaBase):
    produto_id: int = Field(examples=[10])
    sku: str = Field(examples=["TAP-QUEIJO"])
    nome_produto: str = Field(examples=["Tapioca de queijo coalho"])
    quantidade: int = Field(examples=[48])
    atualizado_em: datetime

    @classmethod
    def de(cls, saldo: SaldoEstoque) -> "SaldoEstoqueResponse":
        return cls(
            produto_id=saldo.produto_id,
            sku=saldo.sku,
            nome_produto=saldo.nome_produto,
            quantidade=saldo.quantidade,
            atualizado_em=saldo.atualizado_em,
        )
