from django.contrib.auth.hashers import make_password
from django.db import models
from django.db.models.functions import Now

from core.managers import EscopoUnidadeManager, ManagerSemEscopo
from core.models import TimeStampedModel, UnidadeScopedModel


class Regiao(models.TextChoices):
    N = "N", "Norte"
    NE = "NE", "Nordeste"
    CO = "CO", "Centro-Oeste"
    SE = "SE", "Sudeste"
    S = "S", "Sul"


class TipoUnidade(models.TextChoices):
    COMPLETA = "COMPLETA", "Cozinha completa"
    REDUZIDA = "REDUZIDA", "Formato reduzido"


class Unidade(TimeStampedModel):
    codigo = models.CharField(max_length=20, unique=True)
    nome = models.CharField(max_length=100)
    cidade = models.CharField(max_length=80)
    uf = models.CharField(max_length=2)
    regiao = models.CharField(max_length=2, choices=Regiao.choices)
    tipo = models.CharField(max_length=10, choices=TipoUnidade.choices)
    ativa = models.BooleanField(default=True)

    objects = EscopoUnidadeManager(campo_escopo="id")
    unscoped = ManagerSemEscopo()

    class Meta:
        db_table = "unidades"
        verbose_name = "unidade"
        verbose_name_plural = "unidades"
        ordering = ["codigo"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(regiao__in=Regiao.values), name="unidades_regiao_valida"
            ),
            models.CheckConstraint(
                condition=models.Q(tipo__in=TipoUnidade.values), name="unidades_tipo_valido"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.codigo} — {self.nome}"

    def possui_cozinha_completa(self) -> bool:
        return self.tipo == TipoUnidade.COMPLETA


class Dispositivo(UnidadeScopedModel):
    nome = models.CharField(max_length=80)
    client_id = models.CharField(max_length=60, unique=True)
    secret_hash = models.CharField(max_length=255)
    ativo = models.BooleanField(default=True)
    ultimo_uso_em = models.DateTimeField(null=True, blank=True)
    criado_em = models.DateTimeField(db_default=Now(), editable=False)

    class Meta:
        db_table = "dispositivos"
        verbose_name = "dispositivo (totem)"
        verbose_name_plural = "dispositivos (totens)"
        ordering = ["client_id"]

    def __str__(self) -> str:
        return self.client_id

    def definir_segredo(self, segredo: str) -> None:
        self.secret_hash = make_password(segredo)
