from django.contrib.admin.apps import AdminConfig


class RaizesAdminConfig(AdminConfig):
    default_site = "core.admin_site.RaizesAdminSite"
