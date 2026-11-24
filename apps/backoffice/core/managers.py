from typing import Any

from django.db import models

from core.escopo import EscopoUnidade, escopo_atual


class EscopoUnidadeManager(models.Manager):
    """Manager padrão dos models com unidade: só devolve linhas do escopo atual.

    Sem escopo declarado (fora de request, sem `escopo_sistema()`), devolve queryset vazio.
    Use `Model.unscoped` apenas quando o acesso irrestrito for intencional.
    """

    use_in_migrations = False

    def __init__(self, campo_escopo: str = "unidade") -> None:
        super().__init__()
        self.campo_escopo = campo_escopo

    def get_queryset(self) -> models.QuerySet[Any]:
        escopo = escopo_atual()
        if escopo is None:
            return super().get_queryset().none()
        return self.no_escopo(escopo)

    def no_escopo(self, escopo: EscopoUnidade) -> models.QuerySet[Any]:
        queryset = super().get_queryset()
        if escopo.ver_todas:
            return queryset
        return queryset.filter(**{f"{self.campo_escopo}__in": escopo.unidade_ids})


class ManagerSemEscopo(models.Manager):
    """Acesso irrestrito, só para uso explícito: seed, comandos, services e consumidores."""
