import uuid

from django.db import models
from django.db.models.functions import Now

from core.managers import EscopoUnidadeManager, ManagerSemEscopo


class TipoAtor(models.TextChoices):
    CLIENTE = "CLIENTE", "Cliente"
    FUNCIONARIO = "FUNCIONARIO", "Funcionário"
    DISPOSITIVO = "DISPOSITIVO", "Dispositivo"
    SISTEMA = "SISTEMA", "Sistema"


class TimeStampedModel(models.Model):
    criado_em = models.DateTimeField(db_default=Now(), editable=False)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UnidadeScopedModel(models.Model):
    unidade = models.ForeignKey("unidades.Unidade", on_delete=models.PROTECT)

    objects = EscopoUnidadeManager()
    unscoped = ManagerSemEscopo()

    class Meta:
        abstract = True


class Auditoria(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ocorrido_em = models.DateTimeField(db_default=Now(), editable=False)
    ator_tipo = models.CharField(max_length=20, choices=TipoAtor.choices)
    ator_id = models.CharField(max_length=64)
    acao = models.CharField(max_length=60)
    entidade = models.CharField(max_length=40)
    entidade_id = models.CharField(max_length=64)
    unidade = models.ForeignKey(
        "unidades.Unidade", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    dados = models.JSONField(default=dict, blank=True)
    request_id = models.CharField(max_length=64, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)

    objects = EscopoUnidadeManager()
    unscoped = ManagerSemEscopo()

    class Meta:
        db_table = "auditoria"
        verbose_name = "registro de auditoria"
        verbose_name_plural = "auditoria"
        ordering = ["-ocorrido_em"]
        indexes = [
            models.Index(fields=["entidade", "entidade_id"], name="auditoria_entidade_idx"),
            models.Index(fields=["unidade", "-ocorrido_em"], name="auditoria_unidade_data_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(ator_tipo__in=TipoAtor.values), name="auditoria_ator_tipo_valido"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.acao} {self.entidade}:{self.entidade_id}"


class OutboxEvento(models.Model):
    """Evento de domínio gravado na mesma transação do comando (outbox pattern, guideline 07).

    Os nomes `aggregatetype`, `aggregateid`, `type` e `payload` seguem o Outbox Event Router do Debezium.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    aggregatetype = models.CharField(max_length=40)
    aggregateid = models.CharField(max_length=64)
    type = models.CharField(max_length=80)
    payload = models.JSONField()
    ocorrido_em = models.DateTimeField(db_default=Now(), editable=False)

    class Meta:
        db_table = "outbox_eventos"
        verbose_name = "evento da outbox"
        verbose_name_plural = "eventos da outbox"
        indexes = [models.Index(fields=["ocorrido_em"], name="outbox_ocorrido_em_idx")]

    def __str__(self) -> str:
        return f"{self.type} {self.aggregatetype}:{self.aggregateid}"
