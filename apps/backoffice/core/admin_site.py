from django.contrib import admin
from django.http import HttpRequest


class RaizesAdminSite(admin.AdminSite):
    site_header = "Raízes do Nordeste — Back-office"
    site_title = "Raízes do Nordeste"
    index_title = "Administração da rede"

    def has_permission(self, request: HttpRequest) -> bool:
        # T1: só superusers entram. O admin com escopo por filial e permissões por grupo é T2 (guideline 06).
        return bool(request.user.is_active and request.user.is_superuser)
