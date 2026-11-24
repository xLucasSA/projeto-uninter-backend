from django.contrib import admin

from contas.models import Funcionario
from core.admin import SomenteLeituraAdmin


@admin.register(Funcionario)
class FuncionarioAdmin(SomenteLeituraAdmin):
    list_display = ["email", "nome", "is_active", "is_staff", "is_superuser"]
    list_filter = ["is_active", "is_staff", "groups"]
    search_fields = ["email", "nome"]
    exclude = ["password", "user_permissions"]
