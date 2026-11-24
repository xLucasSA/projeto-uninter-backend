from typing import Any

from django.contrib import admin
from django.http import HttpRequest

from core.models import Auditoria


class SomenteLeituraAdmin(admin.ModelAdmin):
    def has_add_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False


@admin.register(Auditoria)
class AuditoriaAdmin(SomenteLeituraAdmin):
    list_display = ["ocorrido_em", "acao", "entidade", "entidade_id", "ator_tipo", "ator_id", "unidade"]
    list_filter = ["acao", "entidade"]
    search_fields = ["entidade_id", "request_id"]
    exclude = ["ip"]
