from django.contrib import admin

from core.admin import SomenteLeituraAdmin
from estoque.models import Estoque, MovimentacaoEstoque


@admin.register(Estoque)
class EstoqueAdmin(SomenteLeituraAdmin):
    list_display = ["unidade", "produto", "quantidade", "atualizado_em"]
    search_fields = ["produto__sku", "produto__nome"]


@admin.register(MovimentacaoEstoque)
class MovimentacaoEstoqueAdmin(SomenteLeituraAdmin):
    list_display = [
        "criado_em",
        "unidade",
        "produto",
        "tipo",
        "origem",
        "quantidade",
        "saldo_apos",
        "pedido_id",
    ]
    list_filter = ["tipo", "origem"]
    search_fields = ["produto__sku", "pedido_id"]
