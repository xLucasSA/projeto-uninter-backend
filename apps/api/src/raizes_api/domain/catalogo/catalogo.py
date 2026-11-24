from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from raizes_api.domain.compartilhado.dinheiro import Dinheiro


class TipoMovimentacao(StrEnum):
    ENTRADA = "ENTRADA"
    SAIDA_PEDIDO = "SAIDA_PEDIDO"
    ESTORNO_PEDIDO = "ESTORNO_PEDIDO"
    AJUSTE = "AJUSTE"


class CategoriaProduto(StrEnum):
    TAPIOCA = "TAPIOCA"
    CUSCUZ = "CUSCUZ"
    BOLO = "BOLO"
    PRATO = "PRATO"
    BEBIDA = "BEBIDA"
    CAFE = "CAFE"
    COMBO = "COMBO"


@dataclass(frozen=True, slots=True)
class Unidade:
    id: int
    codigo: str
    esta_ativa: bool


@dataclass(frozen=True, slots=True)
class OfertaNaUnidade:
    """Um produto visto pelo cardápio de uma unidade. `preco` nulo: o produto não está nesse cardápio."""

    produto_id: int
    nome_produto: str
    produto_ativo: bool
    preco: Dinheiro | None
    cardapio_ativo: bool
    disponivel_de: date | None = None
    disponivel_ate: date | None = None

    def vendavel_em(self, dia: date) -> bool:
        return self.preco_em(dia) is not None

    def preco_em(self, dia: date) -> Dinheiro | None:
        """Preço de venda no dia; None se o produto não pode ser vendido nesta unidade nesse dia."""
        if not (self.produto_ativo and self.cardapio_ativo):
            return None
        depois_do_inicio = self.disponivel_de is None or dia >= self.disponivel_de
        antes_do_fim = self.disponivel_ate is None or dia <= self.disponivel_ate
        return self.preco if depois_do_inicio and antes_do_fim else None
