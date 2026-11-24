from django.contrib import admin

from catalogo.models import CardapioUnidade, Produto
from core.admin import SomenteLeituraAdmin


@admin.register(Produto)
class ProdutoAdmin(SomenteLeituraAdmin):
    list_display = ["sku", "nome", "categoria", "requer_cozinha_completa", "ativo"]
    list_filter = ["categoria", "ativo"]
    search_fields = ["sku", "nome"]


@admin.register(CardapioUnidade)
class CardapioUnidadeAdmin(SomenteLeituraAdmin):
    list_display = ["unidade", "produto", "preco", "ativo", "disponivel_de", "disponivel_ate"]
    list_filter = ["ativo"]
    search_fields = ["produto__sku", "produto__nome"]
