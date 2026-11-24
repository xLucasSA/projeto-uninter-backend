from django.contrib import admin

from core.admin import SomenteLeituraAdmin
from unidades.models import Dispositivo, Unidade


@admin.register(Unidade)
class UnidadeAdmin(SomenteLeituraAdmin):
    list_display = ["codigo", "nome", "cidade", "uf", "regiao", "tipo", "ativa"]
    list_filter = ["regiao", "tipo", "ativa"]
    search_fields = ["codigo", "nome", "cidade"]


@admin.register(Dispositivo)
class DispositivoAdmin(SomenteLeituraAdmin):
    list_display = ["client_id", "nome", "unidade", "ativo", "ultimo_uso_em"]
    list_filter = ["ativo"]
    exclude = ["secret_hash"]
